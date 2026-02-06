import { NextResponse } from 'next/server'
import path from 'path'
import fs from 'fs/promises'

const allowedPattern = /^(valid_F\d{3}|sample_\d{3})\.png$/

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const name = searchParams.get('name') || ''

  if (!allowedPattern.test(name)) {
    return NextResponse.json({ error: 'Invalid sample name' }, { status: 400 })
  }

  const samplesDir = path.resolve(process.cwd(), '..', 'backend', 'data', 'samples')
  const filePath = path.join(samplesDir, name)

  try {
    const data = await fs.readFile(filePath)
    return new NextResponse(data, {
      headers: {
        'Content-Type': 'image/png',
        'Cache-Control': 'no-store',
      },
    })
  } catch {
    return NextResponse.json({ error: 'Sample not found' }, { status: 404 })
  }
}
