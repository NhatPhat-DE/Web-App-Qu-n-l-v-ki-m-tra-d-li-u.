const reasonMessages: Record<string,string> = {
  BATCH_DIFFERENT: 'Hai đợt khác nhau.',
  ENGINE_VERSION_DIFFERENT: 'Cách kiểm tra đã thay đổi.',
  RULE_REVISION_DIFFERENT: 'Bộ quy tắc đã thay đổi.',
  RULE_SET_FINGERPRINT_DIFFERENT: 'Bộ quy tắc đã thay đổi.',
}

/** Different technical codes may describe the same business reason. */
export function comparisonReasonMessages(reasons: string[]): string[] {
  return [...new Set(reasons.map(reason=>reasonMessages[reason] ?? `Điều kiện đối chiếu khác: ${reason}.`))]
}
