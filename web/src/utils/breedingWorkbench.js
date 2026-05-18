export const DEFAULT_SMOKE_BREEDING_CONTEXT = {
  data_dir: '/mnt/yuxi-breeding-data/smoke_test_minimal/Si9g037800_smoke_test_minimal',
  reference_genome: 'genome.fa',
  genome_gff: 'genome.gff',
  function_annotation: 'xiaomi_T2T_Annotation.smoke_genes.txt',
  rnaseq_reads: 'fq/*.fq.gz',
  sample_map: 'sampleName_clientId.txt',
  usage_doc: 'USAGE_run_smoke_de_pipeline.md',
  metabolome_tsv: 'metabolome_raw_3372.tsv',
  trait: '黄酮相关',
  user_question: '给出一些育种建议'
}

export const REQUIRED_BREEDING_FIELDS = [
  { key: 'reference_genome', label: '参考基因组' },
  { key: 'genome_gff', label: '基因组注释' },
  { key: 'function_annotation', label: '基因功能注释' },
  { key: 'rnaseq_reads', label: 'RNA-seq Reads' },
  { key: 'sample_map', label: '数据标签' },
  { key: 'usage_doc', label: '流程说明' },
  { key: 'metabolome_tsv', label: '代谢含量' },
  { key: 'trait', label: '性状输入' },
  { key: 'user_question', label: '用户问题' }
]

const DOI_REGEX = /10\.\d{4,9}\/[^\s，,；;）)\]】"'“”‘’]+/gi

const normalizeQuotedText = (value = '') => value.replace(/^[“"'‘’\s]+|[”"'‘’\s]+$/g, '').trim()
const cleanDoiValue = (value = '') => value.replace(/[，,；;。)\]】>"'“”‘’]+$/g, '').trim()

const downloadContent = (filename, content, mimeType) => {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export const extractLiteratureEvidence = (markdown = '') => {
  if (typeof markdown !== 'string' || !markdown.trim()) return []

  const blocks = markdown
    .split(/\n(?=(?:###\s*)?(?:证据|Evidence)\s*\d+)/i)
    .map((item) => item.trim())
    .filter((item) => /(?:证据|Evidence)\s*\d+/i.test(item))

  const parsed = []
  for (const block of blocks) {
    const doiMatch = block.match(/(?:真实\s*)?DOI[：:]\s*(10\.\d{4,9}\/[^\s，,；;）)\]】"'“”‘’]+)/i)
    const quoteMatch = block.match(
      /(?:引用原文|引用原句|quoted_sentence|quote|原文|引用)[：:]\s*([^\n]+)/i
    )
    const doi = cleanDoiValue((doiMatch?.[1] || '').trim())
    const quote = normalizeQuotedText((quoteMatch?.[1] || '').trim())
    const title = (block.match(/(?:文献标题|title)[：:]\s*([^\n]+)/i)?.[1] || '').trim()
    if (!doi || !quote) continue
    parsed.push({ doi, quote, title })
  }

  if (parsed.length > 0) return parsed

  const lines = markdown.split('\n')
  const fallback = []
  for (let index = 0; index < lines.length; index += 1) {
    const doi = cleanDoiValue(
      (lines[index].match(/(?:真实\s*)?DOI[：:]\s*(10\.\d{4,9}\/[^\s，,；;）)\]】"'“”‘’]+)/i)?.[1] || '').trim()
    )
    if (!doi) continue

    let quote = ''
    let title = ''
    for (let inner = index + 1; inner < Math.min(index + 8, lines.length); inner += 1) {
      if (!quote) {
        quote = normalizeQuotedText(
          (
            lines[inner].match(/(?:引用原文|引用原句|quoted_sentence|quote|原文|引用)[：:]\s*([^\n]+)/i)?.[1] || ''
          ).trim()
        )
      }
      if (!title) title = (lines[inner].match(/(?:文献标题|title)[：:]\s*([^\n]+)/i)?.[1] || '').trim()
    }
    if (quote) fallback.push({ doi, quote, title })
  }

  const deduped = []
  const seen = new Set()
  for (const item of fallback) {
    const key = `${item.doi}::${item.quote}`
    if (!item.doi || !item.quote || seen.has(key)) continue
    seen.add(key)
    deduped.push(item)
  }
  return deduped
}

export const evaluateBreedingCompliance = (markdown = '') => {
  const hasDoi = DOI_REGEX.test(markdown) || markdown.includes('10.3390') || markdown.includes('10.1186')
  DOI_REGEX.lastIndex = 0

  const hasQuote =
    markdown.includes('The yellow pigment mainly includes carotenoids (lutein and zeaxanthin) and flavonoids.') ||
    markdown.includes(
      'Foxtail millet (Setaria italica L.), a traditional Chinese crop, is valued for its rich abundance of health-beneficial compounds (e.g., flavonoids).'
    ) ||
    markdown.includes('引用原句') ||
    markdown.includes('引用原文')

  const hasBoundary =
    markdown.includes('未完成') ||
    markdown.includes('不是') ||
    markdown.includes('不能声称') ||
    markdown.includes('后续') ||
    markdown.includes('直接功能验证')

  return [
    { key: 'gene', label: 'Si9g037800', passed: markdown.includes('Si9g037800') },
    { key: 'population', label: '群体', passed: markdown.includes('群体') },
    { key: 'trait', label: '黄酮', passed: markdown.includes('黄酮') },
    { key: 'doi', label: 'DOI', passed: hasDoi },
    { key: 'quote', label: '引用原文', passed: hasQuote },
    { key: 'boundary', label: '边界说明', passed: hasBoundary }
  ]
}

export const downloadMarkdown = (filename, content) => {
  downloadContent(filename, content, 'text/markdown;charset=utf-8')
}

export const downloadTsv = (filename, content) => {
  downloadContent(filename, content, 'text/tab-separated-values;charset=utf-8')
}
