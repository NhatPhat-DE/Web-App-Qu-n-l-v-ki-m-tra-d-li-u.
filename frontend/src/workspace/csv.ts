import Papa from 'papaparse'
import { isWhitespaceOnly } from './cellPresentation'
export interface CSVPreview { header: string[]; rows: string[][]; rowCount: number }
export async function previewCSV(file: File): Promise<CSVPreview> {
  if (!file.name.toLowerCase().endsWith('.csv')) throw new Error('Hãy chọn file có phần mở rộng .csv.')
  if (file.size > 5 * 1024 * 1024) throw new Error('File vượt giới hạn 5 MiB.')
  let content: string
  try { content = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer()) } catch { throw new Error('Không đọc được file. Hãy lưu file với mã hóa UTF-8 hoặc UTF-8 BOM.') }
  return parseCSVText(content)
}
export function parseCSVText(content: string): CSVPreview {
  content = content.replace(/^\uFEFF/, '')
  if (!content.length) throw new Error('File CSV rỗng, chưa có dòng tiêu đề.')
  if (content.includes('\0')) throw new Error('File chứa ký tự không được hỗ trợ (NUL).')
  // Validate quote positions too: Papa deliberately accepts quotes in unquoted fields,
  // while the backend rejects them. Papa remains responsible for parsing records.
  let state: 'start' | 'plain' | 'quoted' | 'closed' = 'start'
  let recordStart = 0
  for (let i = 0; i < content.length; i++) {
    const char = content[i]
    if (state === 'quoted') { if (char === '"') { if (content[i + 1] === '"') i++; else state = 'closed' }; continue }
    if (char === '\r' || char === '\n') {
      if (i === recordStart) throw new Error('Không để dòng hoàn toàn trống trong CSV.')
      if (char === '\r' && content[i + 1] === '\n') i++
      recordStart = i + 1; state = 'start'; continue
    }
    if (char === ',') { state = 'start'; continue }
    if (state === 'closed' || char === '"' && state !== 'start') throw new Error('Dấu ngoặc kép trong CSV không hợp lệ.')
    state = char === '"' ? 'quoted' : 'plain'
  }
  if (state === 'quoted') throw new Error('File có trường chưa đóng dấu ngoặc kép.')
  const result = Papa.parse<string[]>(content, { delimiter: ',', skipEmptyLines: false, dynamicTyping: false })
  if (result.errors.length) throw new Error('Cú pháp CSV không hợp lệ. Kiểm tra dấu ngoặc kép và dấu phân cách.')
  const records = result.data
  if (/\r\n$|[\r\n]$/.test(content) && records.at(-1)?.length === 1 && records.at(-1)?.[0] === '') records.pop()
  const header = records.shift() ?? []
  if (!header.length || header.some(name => !name.trim())) throw new Error('Dòng tiêu đề có tên cột rỗng. Mỗi cột cần một tên.')
  if (new Set(header).size !== header.length) throw new Error('Tên cột bị trùng. Hãy đặt tên riêng cho từng cột.')
  if (!records.length) throw new Error('File phải có ít nhất một bản ghi ngoài dòng tiêu đề.')
  if (records.length > 10000) throw new Error('File vượt giới hạn 10.000 bản ghi.')
  const invalid = records.findIndex(row => row.length !== header.length || row.length === 1 && row[0] === '' && header.length > 1)
  if (invalid >= 0) throw new Error(`Bản ghi ${invalid + 1} sai số cột: cần ${header.length} cột. Không để dòng trống.`)
  return { header, rows: records.slice(0, 10), rowCount: records.length }
}
export function csvBlob(rows: unknown[][]) {
  return new Blob(['\uFEFF', Papa.unparse(rows.map(row => row.map(value => {
    const text = value == null ? '' : String(value)
    // Pure whitespace cannot execute a formula; preserve it for source auditing.
    return (/^[\s\uFEFF]*[=+\-@]/u.test(text) || /^[\t\r\n]/.test(text)) && !isWhitespaceOnly(text) ? `'${text}` : text
  })))], { type: 'text/csv;charset=utf-8' })
}
export const samples: Record<string, { filename: string; content: string }> = {
  customers: { filename: 'khach-hang-co-loi.csv', content: 'ma_kh,ten_kh,email,ngay_dang_ky\r\nKH001,Khách hàng mẫu A,mau-a@example.com,2026-01-15\r\n,Khách hàng mẫu B,sai-email,2026-02-30\r\nKH003,"Khách hàng mẫu C, chi nhánh 1",mau-c@example.com,2026-03-01\r\nKH003,Khách hàng mẫu D,mau-d@example.com,01/03/2026\r\n' },
  fixed: { filename: 'khach-hang-da-sua.csv', content: 'ma_kh,ten_kh,email,ngay_dang_ky\r\nKH001,Khách hàng mẫu A,mau-a@example.com,2026-01-15\r\nKH002,Khách hàng mẫu B,mau-b@example.com,2026-02-28\r\nKH003,"Khách hàng mẫu C, chi nhánh 1",mau-c@example.com,2026-03-01\r\nKH004,Khách hàng mẫu D,mau-d@example.com,2026-03-01\r\n' },
  products: { filename: 'san-pham-mau.csv', content: 'ma_sp,ten_sp,don_gia\r\nSP001,Sổ tay mẫu,35000\r\nSP002,Bút mực mẫu,12000\r\n' },
  orders: { filename: 'don-hang-mau.csv', content: 'ma_don,ma_kh,ngay_dat,tong_tien\r\nDH001,KH001,2026-03-01,47000\r\nDH002,KH002,2026-03-02,35000\r\n' },
}
