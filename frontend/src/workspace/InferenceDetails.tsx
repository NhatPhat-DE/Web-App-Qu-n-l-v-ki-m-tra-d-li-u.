import type { DatasetVersion } from '../api/datasets'
import { Badge, number, typeLabels } from './ui'

export default function InferenceDetails({ version, column }: { version?: DatasetVersion; column: string }) {
  const inference = version?.inferred_types?.find(item => item.column_name === column)
  return <><Badge>{typeLabels[inference?.inferred_type ?? 'unknown']}</Badge>{inference && <details className="inference-details"><summary>Chi tiết suy luận</summary><dl><div><dt>Phiên bản</dt><dd>v{version!.version_number}</dd></div><div><dt>Giá trị không thiếu</dt><dd>{number(inference.non_missing_count)}</dd></div><div><dt>Giá trị thiếu</dt><dd>{number(inference.missing_count)}</dd></div></dl></details>}</>
}
