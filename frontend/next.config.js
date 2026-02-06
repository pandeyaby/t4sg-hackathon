/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow API calls to backend
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8004/:path*',
      },
    ]
  },
}

module.exports = nextConfig
