import { describe, it, expect } from 'vitest'
import { detectRoleLevel } from '../composables/useRoleLevel'

describe('detectRoleLevel', () => {
  it('detects graduate from "Graduate Data Engineer"', () => {
    expect(detectRoleLevel('Graduate Data Engineer at Capgemini')).toBe('graduate')
  })
  it('detects graduate from intern keyword', () => {
    expect(detectRoleLevel('Summer 2026 Software Engineering Intern')).toBe('graduate')
  })
  it('maps junior to graduate', () => {
    expect(detectRoleLevel('Junior Backend Developer')).toBe('graduate')
  })
  it('detects non-graduate from senior keyword', () => {
    expect(detectRoleLevel('Senior ML Engineer')).toBe('non-graduate')
  })
  it('detects non-graduate from principal keyword', () => {
    expect(detectRoleLevel('Principal Software Engineer')).toBe('non-graduate')
  })
  it('detects non-graduate from tech lead', () => {
    expect(detectRoleLevel('Tech Lead — Platform team')).toBe('non-graduate')
  })
  it('graduate when years ≤ 2', () => {
    expect(detectRoleLevel('Looking for 2 years of experience')).toBe('graduate')
  })
  it('non-graduate when years ≥ 3', () => {
    expect(detectRoleLevel('5+ years experience required')).toBe('non-graduate')
  })
  it('returns null when no signal', () => {
    expect(detectRoleLevel('We hire great people')).toBeNull()
  })
})
