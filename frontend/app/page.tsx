'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileCheck, AlertCircle, CheckCircle, Loader2, Camera, RefreshCw } from 'lucide-react'

interface QualityResult {
  is_acceptable: boolean
  blur_score: number
  brightness_score: number
  glare_score: number
  angle_score: number
  resolution_ok: boolean
  issues: string[]
  suggestions: string[]
}

interface OCRResult {
  raw_text: string
  detected_language: string
  confidence: number
  fields: Record<string, string | null>
  ocr_engine: string
}

interface ValidationResult {
  is_valid: boolean
  confidence: number
  matched_farmer: Record<string, string> | null
  field_matches: Record<string, { valid: boolean; confidence: number }>
  issues: string[]
  warnings: string[]
}

interface VerificationResponse {
  success: boolean
  quality: QualityResult
  ocr_result: OCRResult | null
  validation: ValidationResult | null
  summary: string
  next_steps: string[]
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<VerificationResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (file) {
      setFile(file)
      setPreview(URL.createObjectURL(file))
      setResult(null)
      setError(null)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpeg', '.jpg', '.png'] },
    maxFiles: 1,
  })

  const handleVerify = async () => {
    if (!file) return

    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/api/verify', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Verification failed')
      }

      const data: VerificationResponse = await response.json()
      setResult(data)
    } catch (err) {
      setError('Failed to verify document. Please ensure the backend is running.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setFile(null)
    setPreview(null)
    setResult(null)
    setError(null)
  }

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-green-600'
    if (score >= 40) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getScoreBg = (score: number) => {
    if (score >= 70) return 'bg-green-100'
    if (score >= 40) return 'bg-yellow-100'
    return 'bg-red-100'
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Hero Section */}
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-forest-800 mb-2">
          Verify Farmer Documents Instantly
        </h2>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Upload land records, bank details, or identity documents. Our AI extracts information 
          in Hindi, Marathi, and English — even from handwritten documents.
        </p>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Left Column: Upload */}
        <div className="space-y-6">
          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={`
              border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
              transition-all duration-200 ease-in-out
              ${isDragActive 
                ? 'border-forest-500 bg-forest-50' 
                : 'border-gray-300 hover:border-forest-400 hover:bg-forest-50/50'
              }
              ${preview ? 'border-solid border-forest-300' : ''}
            `}
          >
            <input {...getInputProps()} />
            
            {preview ? (
              <div className="space-y-4">
                <img 
                  src={preview} 
                  alt="Document preview" 
                  className="max-h-64 mx-auto rounded-lg shadow-md"
                />
                <p className="text-sm text-gray-500">{file?.name}</p>
                <p className="text-xs text-forest-600">Click or drag to replace</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="w-16 h-16 mx-auto bg-forest-100 rounded-full flex items-center justify-center">
                  <Upload className="w-8 h-8 text-forest-600" />
                </div>
                <div>
                  <p className="text-lg font-medium text-gray-700">
                    Drop your document here
                  </p>
                  <p className="text-sm text-gray-500">
                    or click to browse
                  </p>
                </div>
                <div className="flex items-center justify-center space-x-4 text-xs text-gray-400">
                  <span>JPG</span>
                  <span>•</span>
                  <span>PNG</span>
                  <span>•</span>
                  <span>Max 10MB</span>
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-4">
            <button
              onClick={handleVerify}
              disabled={!file || loading}
              className={`
                flex-1 py-3 px-6 rounded-lg font-medium text-white
                flex items-center justify-center space-x-2
                transition-all duration-200
                ${file && !loading
                  ? 'bg-forest-600 hover:bg-forest-700 shadow-lg hover:shadow-xl'
                  : 'bg-gray-300 cursor-not-allowed'
                }
              `}
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <FileCheck className="w-5 h-5" />
                  <span>Verify Document</span>
                </>
              )}
            </button>
            
            {(file || result) && (
              <button
                onClick={handleReset}
                className="py-3 px-6 rounded-lg font-medium text-forest-700 bg-forest-100 
                         hover:bg-forest-200 transition-all duration-200 flex items-center space-x-2"
              >
                <RefreshCw className="w-5 h-5" />
                <span>Reset</span>
              </button>
            )}
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-red-800 font-medium">Error</p>
                <p className="text-red-600 text-sm">{error}</p>
              </div>
            </div>
          )}

          {/* Tips */}
          <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
            <h4 className="font-medium text-blue-800 mb-2 flex items-center">
              <Camera className="w-4 h-4 mr-2" />
              Tips for best results
            </h4>
            <ul className="text-sm text-blue-700 space-y-1">
              <li>• Ensure good lighting without glare</li>
              <li>• Keep the document flat and aligned</li>
              <li>• Include all four corners in the frame</li>
              <li>• Avoid blurry or shaky photos</li>
            </ul>
          </div>
        </div>

        {/* Right Column: Results */}
        <div className="space-y-6">
          {result ? (
            <>
              {/* Summary Card */}
              <div className={`
                rounded-xl p-6 shadow-lg
                ${result.success 
                  ? 'bg-gradient-to-br from-green-50 to-green-100 border border-green-200' 
                  : 'bg-gradient-to-br from-yellow-50 to-orange-50 border border-yellow-200'
                }
              `}>
                <div className="flex items-start space-x-4">
                  {result.success ? (
                    <div className="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center animate-pulse-green">
                      <CheckCircle className="w-7 h-7 text-white" />
                    </div>
                  ) : (
                    <div className="w-12 h-12 bg-yellow-500 rounded-full flex items-center justify-center">
                      <AlertCircle className="w-7 h-7 text-white" />
                    </div>
                  )}
                  <div>
                    <h3 className={`text-xl font-bold ${result.success ? 'text-green-800' : 'text-yellow-800'}`}>
                      {result.summary}
                    </h3>
                    {result.validation?.matched_farmer && (
                      <p className="text-green-700 mt-1">
                        District: {result.validation.matched_farmer.district || 'N/A'}, 
                        Village: {result.validation.matched_farmer.village || 'N/A'}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Quality Scores */}
              <div className="bg-white rounded-xl p-6 shadow-md border border-gray-100">
                <h4 className="font-semibold text-gray-800 mb-4">📊 Quality Assessment</h4>
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { label: 'Sharpness', score: result.quality.blur_score },
                    { label: 'Brightness', score: result.quality.brightness_score },
                    { label: 'Glare', score: result.quality.glare_score },
                    { label: 'Alignment', score: result.quality.angle_score },
                  ].map(({ label, score }) => (
                    <div key={label} className={`p-3 rounded-lg ${getScoreBg(score)}`}>
                      <div className="text-sm text-gray-600">{label}</div>
                      <div className={`text-2xl font-bold ${getScoreColor(score)}`}>
                        {score.toFixed(0)}
                      </div>
                    </div>
                  ))}
                </div>
                {result.quality.issues.length > 0 && (
                  <div className="mt-4 text-sm text-yellow-700">
                    <strong>Issues:</strong> {result.quality.issues.join(', ')}
                  </div>
                )}
              </div>

              {/* Extracted Fields */}
              {result.ocr_result && (
                <div className="bg-white rounded-xl p-6 shadow-md border border-gray-100">
                  <h4 className="font-semibold text-gray-800 mb-4">
                    📝 Extracted Information
                    <span className="ml-2 text-sm font-normal text-gray-500">
                      ({result.ocr_result.detected_language === 'hi' ? 'Hindi' : 
                        result.ocr_result.detected_language === 'mr' ? 'Marathi' : 'English'} detected)
                    </span>
                  </h4>
                  <div className="space-y-3">
                    {Object.entries(result.ocr_result.fields).map(([key, value]) => (
                      value && (
                        <div key={key} className="flex justify-between items-center py-2 border-b border-gray-100">
                          <span className="text-gray-600 capitalize">{key.replace(/_/g, ' ')}</span>
                          <span className="font-medium text-gray-800">{value}</span>
                        </div>
                      )
                    ))}
                  </div>
                  <div className="mt-4 text-sm text-gray-500">
                    Confidence: {(result.ocr_result.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              )}

              {/* Next Steps */}
              {result.next_steps.length > 0 && (
                <div className="bg-white rounded-xl p-6 shadow-md border border-gray-100">
                  <h4 className="font-semibold text-gray-800 mb-3">📌 Next Steps</h4>
                  <ul className="space-y-2">
                    {result.next_steps.map((step, i) => (
                      <li key={i} className="flex items-start space-x-2 text-gray-700">
                        <span className="text-forest-500">•</span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            /* Placeholder when no results */
            <div className="bg-gray-50 rounded-xl p-8 text-center border-2 border-dashed border-gray-200">
              <div className="w-16 h-16 mx-auto bg-gray-100 rounded-full flex items-center justify-center mb-4">
                <FileCheck className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-600 mb-2">
                Verification Results
              </h3>
              <p className="text-gray-400 text-sm">
                Upload a document and click "Verify" to see results here
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Features Section */}
      <div className="mt-16 grid md:grid-cols-3 gap-8">
        {[
          {
            icon: '🔤',
            title: 'Multilingual OCR',
            desc: 'Extracts text from Hindi, Marathi, and English documents including handwritten text'
          },
          {
            icon: '✅',
            title: 'Smart Validation',
            desc: 'Fuzzy matching against farmer database catches typos and validates data automatically'
          },
          {
            icon: '📱',
            title: 'Mobile Ready',
            desc: 'Works on any device — field workers can verify documents directly from their phones'
          },
        ].map((feature) => (
          <div key={feature.title} className="text-center p-6">
            <div className="text-4xl mb-4">{feature.icon}</div>
            <h3 className="font-semibold text-gray-800 mb-2">{feature.title}</h3>
            <p className="text-gray-600 text-sm">{feature.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
