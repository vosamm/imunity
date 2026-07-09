import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "암환우 복지 매칭 (MVP)",
  description:
    "중앙부처·지자체 공공 복지 정보를 암환우 관점에서 검색·필터링하는 MVP. 확정 판정이 아닌 참고용입니다.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <head>
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.css"
        />
      </head>
      {/* suppressHydrationWarning: 브라우저 확장(예: ColorZilla의 cz-shortcut-listen)이
          <body>에 속성을 주입해 생기는 hydration 불일치 경고를 무시한다. 앱 코드와 무관. */}
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
