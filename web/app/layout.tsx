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
      <body>{children}</body>
    </html>
  );
}
