import { NextResponse } from 'next/server'
import path from 'path'
import fs from 'fs/promises'

export async function GET() {
  const samplesDir = path.resolve(process.cwd(), '..', 'backend', 'data', 'samples')
  try {
    const files = await fs.readdir(samplesDir)
    const validSamples = files
      .filter((name) => /^valid_F\d{3}\.png$/.test(name))
      .sort()
    return NextResponse.json({ validSamples })
  } catch {
    return NextResponse.json({ validSamples: [] })
  }
}
