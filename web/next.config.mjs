/** @type {import('next').NextConfig} */
const nextConfig = {
  // better-sqlite3는 네이티브 모듈이므로 서버 외부 번들에서 제외한다 (클라이언트 번들 유입 방지).
  serverExternalPackages: ["better-sqlite3"],
};

export default nextConfig;
