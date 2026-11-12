import { describeCell } from './cellPresentation'

/** Presentation only: never pass these labels to persistence or CSV export. */
export default function CellValue({ value }: { value: unknown }) {
  const display = describeCell(value)
  return <span className={display.placeholder ? 'muted' : undefined} title={display.title}>{display.text}</span>
}
