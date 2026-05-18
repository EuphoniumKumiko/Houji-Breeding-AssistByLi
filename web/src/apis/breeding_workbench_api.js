import { agentApi, threadApi } from './agent_api'

const TERMINAL_RUN_STATUSES = new Set([
  'completed',
  'succeeded',
  'failed',
  'cancelled',
  'interrupted',
  'error'
])
const TOOL_NAME_REGEX = /\b(?:smoke|breeding)_[a-z0-9_]+\b/g
const POLL_INTERVAL_MS = 2000
export const NORMAL_WAIT_MS = 180000
export const HARD_TIMEOUT_MS = 420000

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

// Agent history 里消息内容的结构并不稳定，可能是纯字符串，也可能是富文本数组。
// 工作台最终展示必须尽量从真实历史消息中恢复，而不是依赖前端手写模板。
const extractMessageContent = (message) => {
  if (!message) return ''
  if (typeof message.content === 'string') return message.content.trim()
  if (Array.isArray(message.content)) {
    return message.content
      .map((item) => {
        if (typeof item === 'string') return item
        if (typeof item?.text === 'string') return item.text
        return ''
      })
      .filter(Boolean)
      .join('\n')
      .trim()
  }
  return ''
}

const pushUniqueToolName = (target, seen, name, inferred = false) => {
  if (typeof name !== 'string') return
  const normalized = name.trim()
  if (!normalized || seen.has(normalized)) return
  seen.add(normalized)
  target.push({ name: normalized, inferred })
}

const extractToolNamesFromText = (content = '') => {
  if (typeof content !== 'string' || !content.trim()) return []
  return Array.from(content.matchAll(TOOL_NAME_REGEX)).map((match) => match[0])
}

const normalizeHistoryResponse = (historyResponse) => {
  if (Array.isArray(historyResponse)) return historyResponse
  if (Array.isArray(historyResponse?.history)) return historyResponse.history
  return []
}

const extractToolDataFromHistory = (history = []) => {
  const toolCalls = []
  const actualToolChain = []
  const inferredToolChain = []
  const actualSeen = new Set()
  const inferredSeen = new Set()

  for (const item of history) {
    if (!item) continue

    if (Array.isArray(item.tool_calls)) {
      for (const toolCall of item.tool_calls) {
        if (!toolCall?.name) continue
        toolCalls.push(toolCall)
        pushUniqueToolName(actualToolChain, actualSeen, toolCall.name)
      }
    }

    pushUniqueToolName(actualToolChain, actualSeen, item.tool_name)
    pushUniqueToolName(actualToolChain, actualSeen, item.name)
    pushUniqueToolName(actualToolChain, actualSeen, item?.tool_call?.name)

    for (const name of extractToolNamesFromText(extractMessageContent(item))) {
      if (actualSeen.has(name)) continue
      pushUniqueToolName(inferredToolChain, inferredSeen, name, true)
    }
  }

  return { toolCalls, actualToolChain, inferredToolChain }
}

const extractToolDataFromRunState = (runState) => {
  const actualToolChain = []
  const actualSeen = new Set()
  const candidates = []

  if (Array.isArray(runState?.tools)) candidates.push(...runState.tools)
  if (Array.isArray(runState?.steps)) candidates.push(...runState.steps)
  if (Array.isArray(runState?.events)) candidates.push(...runState.events)

  for (const item of candidates) {
    if (!item) continue
    pushUniqueToolName(actualToolChain, actualSeen, item.tool_name)
    pushUniqueToolName(actualToolChain, actualSeen, item.name)
    pushUniqueToolName(actualToolChain, actualSeen, item?.tool?.name)
  }

  return actualToolChain
}

const extractFinalRenderableMessage = (history = []) => {
  // 优先取 assistant 最终消息；如果模型最后只吐出了 tool 消息，再回退到 tool。
  const aiMessages = history.filter((item) => ['ai', 'assistant'].includes(item?.type))
  for (let index = aiMessages.length - 1; index >= 0; index -= 1) {
    const message = aiMessages[index]
    if (extractMessageContent(message)) {
      return { message, source: 'assistant' }
    }
  }

  const toolMessages = history.filter((item) => item?.type === 'tool')
  for (let index = toolMessages.length - 1; index >= 0; index -= 1) {
    const message = toolMessages[index]
    if (extractMessageContent(message)) {
      return { message, source: 'tool' }
    }
  }

  return { message: null, source: '' }
}

const buildRunSnapshot = ({
  threadId,
  runId,
  runState,
  history,
  startedAt,
  pollingCount,
  softTimeoutReached = false,
  hardTimeoutReached = false
}) => {
  // Run 状态只告诉前端“任务还在不在跑”，真正可展示的自然语言内容通常在 history 里。
  // 因此这里把 runState 和 history 汇总成一个快照，供页面统一渲染。
  const finalRenderable = extractFinalRenderableMessage(history)
  const historyToolData = extractToolDataFromHistory(history)
  const runStateToolChain = extractToolDataFromRunState(runState)
  const mergedToolChain = []
  const mergedSeen = new Set()

  for (const item of [...runStateToolChain, ...historyToolData.actualToolChain, ...historyToolData.inferredToolChain]) {
    pushUniqueToolName(mergedToolChain, mergedSeen, item.name, item.inferred)
  }

  const lastHistoryMessage = history.length > 0 ? history[history.length - 1] : null

  return {
    threadId,
    runId,
    status: String(runState?.status || '').trim(),
    runState,
    history,
    finalMessage: finalRenderable.message,
    finalMessageSource: finalRenderable.source,
    toolCalls: historyToolData.toolCalls,
    toolChain: mergedToolChain,
    markdown: extractMessageContent(finalRenderable.message),
    diagnostics: {
      threadId,
      runId,
      runStatus: String(runState?.status || '').trim(),
      elapsedSeconds: Math.floor((Date.now() - startedAt) / 1000),
      pollingCount,
      lastHistoryMessageRole: lastHistoryMessage?.type || '',
      parsedToolCalls: mergedToolChain.map((item) => item.name),
      softTimeoutReached,
      hardTimeoutReached
    }
  }
}

export const buildBreedingWorkbenchQuery = ({ trait, question, context = {} }) => {
  const trimmedTrait = (trait || '黄酮相关').trim() || '黄酮相关'
  const trimmedQuestion = (question || '给出一些育种建议').trim() || '给出一些育种建议'
  const dataDir = context.data_dir || '/mnt/yuxi-breeding-data/smoke_test_minimal/Si9g037800_smoke_test_minimal'

  return [
    `用户问题：${trimmedQuestion}`,
    '',
    '以下为系统内部执行要求，请勿复述为用户输入模板：',
    '当前是 YuXi 育种工作台黄酮相关示例任务。',
    '请严格按以下步骤执行，不要跳过工具调用：',
    '1. 必须优先调用 smoke_flavonoid_breeding_advice 工具。',
    '2. 调用参数：',
    `   data_dir=${dataDir}`,
    `   trait=${trimmedTrait}`,
    '   out_dir=/tmp/yuxi_runs/smoke_flavonoid_breeding_advice',
    '   run_transcriptome=false',
    '3. 如有必要，可继续调用模块化工具链，但至少必须调用 smoke_flavonoid_breeding_advice。',
    '4. 最终回答必须基于 Tool 返回结果，不得编造 DOI 或引用原句。',
    '5. 最终回答必须包含：Si9g037800、群体、黄酮、文献 DOI、引用原文中的原句。',
    '6. 如果 Tool 返回中存在以下背景证据，必须展示：10.3390/life11060578、10.1186/s12864-025-11780-x。',
    '7. 必须明确说明：文献证据是背景证据，不是 Si9g037800 直接功能验证；当前未完成群体验证；当前未完成湿实验验证；当前未完成最终 KASP/CAPS 标记开发。',
    '8. 回答尽量直接，不要长篇推理，不要输出内部思考过程。',
    '9. 如果 Tool 调用失败，请明确说明失败原因，不要编造成功结果。',
    '',
    `当前示例数据目录：${dataDir}`,
    `当前性状为：${trimmedTrait}`,
    `参考基因组：${context.reference_genome || 'genome.fa'}`,
    `基因组注释：${context.genome_gff || 'genome.gff'}`,
    `基因功能注释：${context.function_annotation || 'xiaomi_T2T_Annotation.smoke_genes.txt'}`,
    `RNA-seq Reads 位于：${context.rnaseq_reads || 'fq'}`,
    `数据标签：${context.sample_map || 'sampleName_clientId.txt'}`,
    `流程说明：${context.usage_doc || 'USAGE_run_smoke_de_pipeline.md'}`,
    `代谢含量：${context.metabolome_tsv || 'metabolome_raw_3372.tsv'}`
  ].join('\n')
}

export const buildRepairQuery = (missingLabels = []) => {
  const suffix = missingLabels.length ? `当前缺失项：${missingLabels.join('、')}。` : ''
  return [
    '你刚才的回答未满足育种工作台输出要求。',
    '请基于已调用工具返回结果重新组织最终回答。',
    '最终回答必须包含：Si9g037800、群体、黄酮、文献 DOI、引用原文中的原句。',
    '必须说明文献为背景证据，不是 Si9g037800 直接功能验证。',
    '不得声称完成群体验证、湿实验验证或最终 KASP/CAPS 标记开发。',
    '请直接输出最终育种建议，不要输出内部推理。',
    suffix
  ]
    .filter(Boolean)
    .join('\n')
}

export const runBreedingWorkbench = async ({
  agentId,
  agentConfigId,
  trait,
  question,
  context = {},
  title = '育种工作台',
  normalWaitMs = NORMAL_WAIT_MS,
  hardTimeoutMs = HARD_TIMEOUT_MS,
  threadId: existingThreadId = '',
  queryOverride = '',
  meta = {},
  onProgress = null,
  onSoftTimeout = null
}) => {
  if (!agentId) {
    throw new Error('缺少可用智能体，请先在系统中配置默认智能体。')
  }
  if (!agentConfigId) {
    throw new Error('缺少可用智能体配置，请先为默认智能体设置可用配置。')
  }

  let threadId = existingThreadId
  if (!threadId) {
    // createThread 的作用：先为本次工作台任务创建一个 YuXi 对话线程。
    // 后续的 Run、历史消息、工具调用链和最终回答都会挂到这个 thread 上。
    const thread = await threadApi.createThread(agentId, title, {
      source: 'breeding-workbench',
      trait,
      agent_config_id: agentConfigId
    })
    threadId = thread?.id
  }

  if (!threadId) {
    throw new Error('创建育种工作台线程失败。')
  }

  const allowedTools = [
    'smoke_flavonoid_breeding_advice',
    'breeding_reference_prepare',
    'breeding_transcriptome_deg',
    'breeding_metabolome_prepare',
    'breeding_literature_evidence',
    'breeding_advice_generate',
    'breeding_validation_plan'
  ]

  // createAgentRun 的作用：告诉后端“在指定 thread 上启动一次异步 Agent Run”。
  // 这一步只负责创建任务，不会同步返回最终育种建议。
  const run = await agentApi.createAgentRun({
    query: queryOverride || buildBreedingWorkbenchQuery({ trait, question, context }),
    agent_config_id: agentConfigId,
    thread_id: threadId,
    meta: {
      source: 'breeding-workbench',
      trait,
      breeding_context: context,
      allowed_tools: allowedTools,
      preferred_tool: 'smoke_flavonoid_breeding_advice',
      ...meta
    }
  })
  const runId = run?.run_id
  if (!runId) {
    throw new Error('创建育种工作台运行失败。')
  }

  let runState = null
  let history = []
  let pollingCount = 0
  let softTimeoutReached = false
  const startedAt = Date.now()

  // 这里使用轮询而不是一次性等待：
  // 1. Agent Run 是异步任务，可能持续数十秒到数分钟；
  // 2. 前端需要持续刷新工具调用链、运行状态和最终消息；
  // 3. getAgentRun 看任务状态，getAgentHistory 看真实输出内容，两者缺一不可。
  while (Date.now() - startedAt < hardTimeoutMs) {
    pollingCount += 1
    // getAgentRun 的作用：读取后端 Run 当前状态，例如 running / completed / failed。
    runState = await agentApi.getAgentRun(runId)
    // getAgentHistory 的作用：读取 thread 上已经落库的消息历史，最终展示内容以这里为准。
    const historyResponse = await agentApi.getAgentHistory(threadId)
    history = normalizeHistoryResponse(historyResponse)
    const status = String(runState?.status || '').trim()

    const snapshot = buildRunSnapshot({
      threadId,
      runId,
      runState,
      history,
      startedAt,
      pollingCount,
      softTimeoutReached,
      hardTimeoutReached: false
    })

    if (typeof onProgress === 'function') {
      await onProgress(snapshot)
    }

    if (TERMINAL_RUN_STATUSES.has(status)) {
      return snapshot
    }

    if (Date.now() - startedAt >= normalWaitMs && !softTimeoutReached) {
      softTimeoutReached = true
      if (typeof onSoftTimeout === 'function') {
        // 软超时：任务运行偏久，但仍允许用户继续等待或主动停止。
        // 硬超时：超过总时长上限，前端直接结束等待并报错。
        const decision = await onSoftTimeout(
          buildRunSnapshot({
            threadId,
            runId,
            runState,
            history,
            startedAt,
            pollingCount,
            softTimeoutReached: true,
            hardTimeoutReached: false
          })
        )
        if (decision === 'stop') {
          try {
            await agentApi.cancelAgentRun(runId)
          } catch {
            // ignore cancel failure and surface a stop message to the UI
          }
          throw new Error('已停止本次运行。')
        }
      }
    }

    await sleep(POLL_INTERVAL_MS)
  }

  if (typeof onProgress === 'function') {
    await onProgress(
      buildRunSnapshot({
        threadId,
        runId,
        runState,
        history,
        startedAt,
        pollingCount,
        softTimeoutReached,
        hardTimeoutReached: true
      })
    )
  }
  // 硬超时只意味着前端停止等待，不代表后端 Run 一定已经异常结束。
  throw new Error('智能体执行时间过长，请检查后端 run 状态或重试。')
}

export const breedingWorkbenchApi = {
  runBreedingWorkbench,
  buildBreedingWorkbenchQuery,
  buildRepairQuery,
  NORMAL_WAIT_MS,
  HARD_TIMEOUT_MS
}

export default breedingWorkbenchApi
