import { describe, expect, it } from 'vitest'

import { taskIdFromQuery } from '@/utils/safetyHistory'

describe('safety history query', () => {
  it('reads a task id from a history detail query', () => {
    expect(taskIdFromQuery({ task: 'TASK-001' })).toBe('TASK-001')
  })

  it('uses the first value for repeated task query parameters', () => {
    expect(taskIdFromQuery({ task: ['TASK-002', 'TASK-003'] })).toBe('TASK-002')
  })

  it('returns null when the query does not contain a task id', () => {
    expect(taskIdFromQuery({})).toBeNull()
  })
})

