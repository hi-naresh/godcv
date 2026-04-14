import { describe, it, expect } from 'vitest'
import { detectSeniority } from '../composables/useSeniority'

describe('detectSeniority', () => {
  it('detects graduate from keywords', () => {
    expect(detectSeniority('Graduate software engineer position')).toBe('graduate')
  })
  it('detects senior from keyword', () => {
    expect(detectSeniority('Senior Backend Engineer with 5+ years')).toBe('senior')
  })
  it('detects mid-level from years range', () => {
    expect(detectSeniority('3-5 years of experience required')).toBe('mid-level')
  })
  it('detects lead from title', () => {
    expect(detectSeniority('Lead Software Engineer to manage a team')).toBe('lead')
  })
  it('detects principal', () => {
    expect(detectSeniority('Principal Engineer driving technical strategy')).toBe('principal')
  })
  it('returns null for ambiguous JD', () => {
    expect(detectSeniority('Software engineer to work on Python projects')).toBeNull()
  })
})
