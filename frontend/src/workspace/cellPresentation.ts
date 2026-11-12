// Python str.strip()/isspace() used by quality_engine.is_missing includes
// U+001C–001F and U+0085, and excludes U+FEFF and U+200B (unlike JS trim).
const engineWhitespace = /^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/u
export const isWhitespaceOnly = (value: string) => engineWhitespace.test(value)

export function describeCell(value: unknown): { text: string; title?: string; placeholder: boolean } {
  if (value == null || value === '') {
    return { text: 'Trống', title: value === null ? 'Giá trị gốc: null' : value === undefined ? 'Không có giá trị' : 'Giá trị gốc: "" · 0 ký tự', placeholder: true }
  }
  if (typeof value === 'string' && isWhitespaceOnly(value)) {
    const escaped = [...value].map(char => `\\u${char.codePointAt(0)!.toString(16).padStart(4, '0')}`).join('')
    return { text: 'Chỉ có khoảng trắng', title: `Giá trị gốc: "${escaped}" · ${[...value].length} ký tự`, placeholder: true }
  }
  return { text: String(value), placeholder: false }
}
