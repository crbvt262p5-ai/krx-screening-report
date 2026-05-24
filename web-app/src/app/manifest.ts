import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "멍칼로리 계산기",
    short_name: "멍칼로리",
    description: "강아지 프로필 기준 사료와 간식 칼로리를 계산하고 기록하는 모바일 우선 앱",
    start_url: "/",
    display: "standalone",
    background_color: "#f6f0e8",
    theme_color: "#c86d39",
    lang: "ko-KR",
    icons: [
      {
        src: "/favicon.ico",
        sizes: "any",
        type: "image/x-icon",
      },
    ],
  };
}
