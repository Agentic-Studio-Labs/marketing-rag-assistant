import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { ContentItem, RepurposeResponse } from '../api/types'

const FORMATS = [
  { id: 'linkedin', label: 'LinkedIn Post' },
  { id: 'email', label: 'Email' },
  { id: 'twitter', label: 'Twitter Thread' },
  { id: 'summary', label: 'Summary' },
]
const TONES = ['professional', 'casual', 'technical', 'friendly']

export default function ContentDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [content, setContent] = useState<ContentItem | null>(null)
  const [similar, setSimilar] = useState<ContentItem[]>([])
  const [error, setError] = useState('')
  const [selectedFormats, setSelectedFormats] = useState<string[]>(['linkedin'])
  const [tone, setTone] = useState('professional')
  const [repurposeResult, setRepurposeResult] = useState<RepurposeResponse | null>(null)
  const [repurposing, setRepurposing] = useState(false)
  const [activeTab, setActiveTab] = useState('')

  useEffect(() => {
    if (!id) return
    api.getContent(id).then(setContent).catch(() => setError('Content not found'))
    api.getSimilar(id).then(setSimilar).catch(() => {})
  }, [id])

  async function handleRepurpose() {
    if (!id || selectedFormats.length === 0) return
    setRepurposing(true); setRepurposeResult(null)
    try {
      const result = await api.repurpose({ content_id: id, formats: selectedFormats, tone, save: true })
      setRepurposeResult(result)
      if (result.generated_content) setActiveTab(Object.keys(result.generated_content)[0] || '')
    } catch (err: unknown) { setError(err instanceof Error ? err.message : String(err)) }
    finally { setRepurposing(false) }
  }

  if (error && !content) return <div className="text-center py-8 text-red-500">{error}</div>
  if (!content) return <div className="text-center py-8 text-muted-foreground">Loading...</div>

  return (
    <div className="max-w-6xl mx-auto flex gap-6">
      <div className="flex-1 min-w-0">
        <button onClick={() => navigate(-1)} className="text-sm text-muted-foreground hover:text-foreground mb-4 inline-block">&larr; Back</button>
        <h1 className="text-2xl font-semibold mb-2">{content.title}</h1>
        <div className="flex gap-2 mb-4 flex-wrap">
          <Tag>{content.content_type}</Tag><Tag>{content.persona}</Tag><Tag>{content.funnel_stage}</Tag>
          {content.performance_score > 0 && <Tag>{content.performance_score}%</Tag>}
        </div>
        {content.summary && <p className="text-muted-foreground text-sm mb-4 italic">{content.summary}</p>}
        <div className="whitespace-pre-wrap text-sm leading-relaxed">{content.body}</div>

        {repurposeResult && repurposeResult.success && (
          <div className="mt-8 border-t border-border pt-6">
            <h2 className="text-lg font-semibold mb-3">Generated Content</h2>
            <div className="flex gap-1 mb-4">
              {Object.keys(repurposeResult.generated_content).map((fmt) => (
                <button key={fmt} onClick={() => setActiveTab(fmt)}
                  className={`px-3 py-1.5 text-sm rounded-md ${activeTab === fmt ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'}`}>
                  {fmt}
                  {repurposeResult.quality_scores[fmt] != null && (
                    <span className="ml-1 opacity-70">({Math.round(repurposeResult.quality_scores[fmt] * 100)}%)</span>
                  )}
                </button>
              ))}
            </div>
            {activeTab && repurposeResult.generated_content[activeTab] && (
              <div className="border border-border rounded-lg p-4 bg-muted/20">
                <pre className="whitespace-pre-wrap text-sm font-sans">{repurposeResult.generated_content[activeTab]}</pre>
              </div>
            )}
          </div>
        )}
        {repurposeResult && !repurposeResult.success && (
          <div className="mt-4 text-red-500 text-sm">Errors: {repurposeResult.errors.join(', ')}</div>
        )}
      </div>

      <div className="w-72 flex-shrink-0 space-y-6">
        <div className="border border-border rounded-lg p-4">
          <h3 className="font-semibold mb-3">Repurpose Content</h3>
          <div className="mb-4">
            <p className="text-xs font-medium text-muted-foreground mb-2">Formats</p>
            {FORMATS.map((f) => (
              <label key={f.id} className="flex items-center gap-2 text-sm mb-1">
                <input type="checkbox" checked={selectedFormats.includes(f.id)}
                  onChange={(e) => setSelectedFormats(e.target.checked ? [...selectedFormats, f.id] : selectedFormats.filter((x) => x !== f.id))} />
                {f.label}
              </label>
            ))}
          </div>
          <div className="mb-4">
            <p className="text-xs font-medium text-muted-foreground mb-2">Tone</p>
            <select value={tone} onChange={(e) => setTone(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm">
              {TONES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <button onClick={handleRepurpose} disabled={repurposing || selectedFormats.length === 0}
            className="w-full rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50">
            {repurposing ? 'Generating...' : 'Generate'}
          </button>
        </div>
        {similar.length > 0 && (
          <div className="border border-border rounded-lg p-4">
            <h3 className="font-semibold mb-3 text-sm">Similar Content</h3>
            {similar.map((s) => (
              <button key={s.id} onClick={() => navigate(`/content/${s.id}`)}
                className="block text-left text-sm text-muted-foreground hover:text-foreground mb-2 w-full">{s.title}</button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function Tag({ children }: { children: React.ReactNode }) {
  return <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground">{children}</span>
}
