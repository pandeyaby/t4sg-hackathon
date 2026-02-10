import { NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8004'

export async function POST(request: Request) {
  const body = await request.json()
  const adminKey = body.adminKey || ''
  const json = body.json || ''

  const response = await fetch(`${BACKEND_URL}/admin/google-credentials`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Admin-Key': adminKey,
    },
    body: JSON.stringify({ json }),
  })

  const data = await response.json().catch(() => ({}))
  return NextResponse.json(data, { status: response.status })
}
