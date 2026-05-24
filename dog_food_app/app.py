from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
DATA_DIR = APP_DIR / "data"
LOG_FILE = DATA_DIR / "daily_logs.json"
PROFILE_FILE = DATA_DIR / "dog_profile.json"
DEFAULT_PORT = int(os.getenv("DOG_FOOD_APP_PORT", "8020"))
DEFAULT_HOST = os.getenv("DOG_FOOD_APP_HOST", "0.0.0.0")
SEARCH_ENDPOINT = "https://world.openfoodfacts.org/cgi/search.pl"
USER_AGENT = "DogTreatCalorieApp/0.1 (Codex prototype)"


@dataclass
class ProductRecord:
    name: str
    brand: str
    total_weight_g: float | None
    total_kcal: float | None
    kcal_per_piece: float | None
    kcal_per_100g: float | None
    product_url: str
    image_url: str
    source_note: str
    match_score: float
    categories: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "brand": self.brand,
            "total_weight_g": self.total_weight_g,
            "total_kcal": self.total_kcal,
            "kcal_per_piece": self.kcal_per_piece,
            "kcal_per_100g": self.kcal_per_100g,
            "product_url": self.product_url,
            "image_url": self.image_url,
            "source_note": self.source_note,
            "match_score": self.match_score,
            "categories": self.categories,
        }


def safe_float(value: Any) -> float | None:
    if value in (None, "", "null"):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_quantity_to_grams(quantity_text: str | None) -> float | None:
    if not quantity_text:
        return None

    normalized = quantity_text.lower().replace(",", ".")
    compact = normalized.replace(" ", "")
    multi_match = re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)(kg|g|mg)", compact)
    if multi_match:
        multiplier = safe_float(multi_match.group(1))
        amount = safe_float(multi_match.group(2))
        unit = multi_match.group(3)
        if multiplier is not None and amount is not None:
            total_value = multiplier * amount
            if unit == "kg":
                return total_value * 1000
            if unit == "mg":
                return total_value / 1000
            return total_value

    single_match = re.search(r"(\d+(?:\.\d+)?)(kg|g|mg)", compact)
    value = safe_float(single_match.group(1) if single_match else None)
    if value is None:
        return None

    if single_match and single_match.group(2) == "kg":
        return value * 1000
    if single_match and single_match.group(2) == "mg":
        return value / 1000
    if single_match and single_match.group(2) == "g":
        return value
    return value


def extract_kcal_per_100g(product: dict[str, Any]) -> float | None:
    nutriments = product.get("nutriments") or {}
    return safe_float(
        nutriments.get("energy-kcal_100g")
        or nutriments.get("energy-kcal")
        or nutriments.get("energy-kcal_value")
    )


def build_total_kcal(product: dict[str, Any], total_weight_g: float | None) -> tuple[float | None, float | None, str]:
    nutriments = product.get("nutriments") or {}
    kcal_100g = extract_kcal_per_100g(product)
    kcal_serving = safe_float(nutriments.get("energy-kcal_serving"))

    if kcal_100g is not None and total_weight_g is not None:
        return round(kcal_100g * total_weight_g / 100, 2), kcal_100g, "100g kcal x total weight"
    if kcal_serving is not None:
        return round(kcal_serving, 2), kcal_100g, "serving kcal"
    return None, kcal_100g, "nutrition data unavailable"


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def score_product(product: dict[str, Any], query: str) -> float:
    name = normalize_text(product.get("product_name") or product.get("generic_name") or "")
    brand = normalize_text(product.get("brands") or "")
    categories = normalize_text(product.get("categories") or "")
    labels = normalize_text(product.get("labels") or "")
    search_text = " ".join(part for part in [name, brand, categories, labels] if part)
    query_tokens = [token for token in re.split(r"\s+", normalize_text(query)) if token]

    score = 0.0
    for token in query_tokens:
        if token in name:
            score += 12
        if token in brand:
            score += 6
        if token in search_text:
            score += 3

    pet_keywords = [
        "dog",
        "dogs",
        "chien",
        "canine",
        "pet",
        "pets",
        "강아지",
        "반려견",
        "애견",
        "사료",
        "간식",
        "treat",
        "treats",
        "snack",
        "snacks",
    ]
    if any(keyword in search_text for keyword in pet_keywords):
        score += 18

    if product.get("nutriments"):
        score += 6
    if parse_quantity_to_grams(product.get("quantity")) is not None:
        score += 6
    if product.get("image_front_small_url") or product.get("image_url"):
        score += 2

    return score


def build_search_queries(query: str) -> list[str]:
    normalized_query = normalize_text(query)
    if not normalized_query:
        return []

    queries = [query]
    pet_tokens = ["dog", "강아지", "반려견", "애견", "pet"]
    if not any(token in normalized_query for token in pet_tokens):
        queries.extend([f"{query} dog", f"{query} 강아지", f"{query} pet"])

    return list(dict.fromkeys(queries))


def fetch_search_payload(query: str) -> list[dict[str, Any]]:
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 12,
        "nocache": 1,
    }
    url = f"{SEARCH_ENDPOINT}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": USER_AGENT})

    with urlopen(request, timeout=15.0) as response:
        payload = json.loads(response.read().decode("utf-8"))

    return payload.get("products") or []


def pick_products(products: list[dict[str, Any]], query: str) -> list[ProductRecord]:
    records: list[ProductRecord] = []

    for product in products:
        name = product.get("product_name") or product.get("generic_name") or "이름 없는 제품"
        brand = product.get("brands") or "-"
        total_weight_g = parse_quantity_to_grams(product.get("quantity"))
        total_kcal, kcal_per_100g, source_note = build_total_kcal(product, total_weight_g)
        image_url = product.get("image_front_small_url") or product.get("image_url") or ""
        code = product.get("code") or ""
        categories = product.get("categories") or "-"
        product_url = f"https://world.openfoodfacts.org/product/{code}" if code else ""
        match_score = round(score_product(product, query), 2)
        records.append(
            ProductRecord(
                name=name,
                brand=brand,
                total_weight_g=total_weight_g,
                total_kcal=total_kcal,
                kcal_per_piece=None,
                kcal_per_100g=kcal_per_100g,
                product_url=product_url,
                image_url=image_url,
                source_note=source_note,
                match_score=match_score,
                categories=categories,
            )
        )

    records.sort(
        key=lambda record: (
            math.isclose(record.match_score, 0.0) is False,
            record.match_score,
            record.total_kcal is not None,
            record.total_weight_g is not None,
        ),
        reverse=True,
    )
    return records[:8]


def search_products(query: str) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}

    for search_query in build_search_queries(query):
        for product in fetch_search_payload(search_query):
            key = str(product.get("code") or "") or normalize_text(
                f"{product.get('product_name') or product.get('generic_name') or ''}|{product.get('brands') or ''}"
            )
            if key and key not in deduped:
                deduped[key] = product

    return [record.to_dict() for record in pick_products(list(deduped.values()), query)]


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_logs() -> list[dict[str, Any]]:
    ensure_data_dir()
    if not LOG_FILE.exists():
        return []

    try:
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_logs(logs: list[dict[str, Any]]) -> None:
    ensure_data_dir()
    LOG_FILE.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")


def load_profile() -> dict[str, Any] | None:
    ensure_data_dir()
    if not PROFILE_FILE.exists():
        return None

    try:
        return json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def save_profile(profile: dict[str, Any]) -> None:
    ensure_data_dir()
    PROFILE_FILE.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


class DogFoodAppHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == "/api/search":
            self.handle_search(parsed.query)
            return
        if parsed.path == "/api/logs":
            self.handle_logs_get()
            return
        if parsed.path == "/api/profile":
            self.handle_profile_get()
            return

        self.serve_static(parsed.path)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == "/api/logs":
            self.handle_logs_post()
            return
        if parsed.path == "/api/profile":
            self.handle_profile_post()
            return
        if parsed.path == "/profile/save":
            self.handle_profile_form_post()
            return

        self.send_error(HTTPStatus.NOT_FOUND, "File not found")

    def handle_search(self, query_string: str) -> None:
        query = parse_qs(query_string).get("q", [""])[0].strip()

        if not query:
            self.send_json({"error": "검색어를 입력해 주세요."}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            results = search_products(query)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            self.send_json(
                {
                    "error": "외부 제품 정보를 가져오지 못했습니다.",
                    "details": str(exc),
                    "query": query,
                    "fallback_search_url": (
                        "https://world.openfoodfacts.org/cgi/search.pl"
                        f"?search_terms={quote(query)}&search_simple=1&action=process"
                    ),
                },
                status=HTTPStatus.BAD_GATEWAY,
            )
            return

        self.send_json({"query": query, "results": results})

    def handle_logs_get(self) -> None:
        logs = load_logs()
        logs.sort(key=lambda item: item.get("saved_at", ""), reverse=True)
        self.send_json({"logs": logs[:20]})

    def handle_profile_get(self) -> None:
        self.send_json({"profile": load_profile()})

    def handle_logs_post(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self.send_json({"error": "저장할 데이터가 없습니다."}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"error": "잘못된 JSON 형식입니다."}, status=HTTPStatus.BAD_REQUEST)
            return

        product_name = str(payload.get("product_name") or "").strip()
        if not product_name:
            self.send_json({"error": "제품명은 필수입니다."}, status=HTTPStatus.BAD_REQUEST)
            return

        logs = load_logs()
        logs.append(payload)
        logs.sort(key=lambda item: item.get("saved_at", ""), reverse=True)
        save_logs(logs[:100])
        self.send_json({"ok": True, "logs": logs[:20]})

    def handle_profile_post(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self.send_json({"error": "저장할 프로필이 없습니다."}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"error": "잘못된 JSON 형식입니다."}, status=HTTPStatus.BAD_REQUEST)
            return

        dog_name = str(payload.get("dog_name") or "").strip()
        dog_weight = safe_float(payload.get("dog_weight"))
        if not dog_name or dog_weight is None or dog_weight <= 0:
            self.send_json({"error": "강아지 이름과 체중을 확인해 주세요."}, status=HTTPStatus.BAD_REQUEST)
            return

        save_profile(payload)
        self.send_json({"ok": True, "profile": payload})

    def handle_profile_form_post(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self.redirect("/")
            return

        raw_body = self.rfile.read(content_length).decode("utf-8")
        form = parse_qs(raw_body)
        payload = {
            "dog_name": (form.get("dog_name") or [""])[0].strip(),
            "dog_weight": safe_float((form.get("dog_weight") or [""])[0]),
            "dog_age_group": (form.get("dog_age_group") or ["adult"])[0],
            "dog_activity": (form.get("dog_activity") or ["1.6"])[0],
        }

        if not payload["dog_name"] or payload["dog_weight"] is None or payload["dog_weight"] <= 0:
            self.redirect("/?profile_error=1")
            return

        save_profile(payload)
        redirect_query = urlencode(
            {
                "profile_saved": 1,
                "dog_name": payload["dog_name"],
                "dog_weight": payload["dog_weight"],
                "dog_age_group": payload["dog_age_group"],
                "dog_activity": payload["dog_activity"],
            }
        )
        self.redirect(f"/?{redirect_query}")

    def serve_static(self, request_path: str) -> None:
        if request_path in ("", "/"):
            target = STATIC_DIR / "index.html"
        else:
            target = (STATIC_DIR / request_path.lstrip("/")).resolve()

        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        content_type = self.guess_content_type(target.suffix)
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    @staticmethod
    def guess_content_type(suffix: str) -> str:
        return {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml",
        }.get(suffix.lower(), "application/octet-stream")

    def log_message(self, format: str, *args: Any) -> None:
        return


def run() -> None:
    server = ThreadingHTTPServer((DEFAULT_HOST, DEFAULT_PORT), DogFoodAppHandler)
    display_host = DEFAULT_HOST if DEFAULT_HOST != "0.0.0.0" else "localhost"
    print(f"Dog Food App running at http://{display_host}:{DEFAULT_PORT}")
    if DEFAULT_HOST == "0.0.0.0":
        print(f"Mobile access enabled on port {DEFAULT_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
