// Ambiguous acknowledgement is not evidence of rollback or permission to resend.
export class UploadAcknowledgementError extends Error {
  constructor(message:string){super(message);this.name='UploadAcknowledgementError'}
}
export interface PendingUpload {filename:string;size:number;rowCount:number;startedAt:string;beforeIds:number[]}
export const pendingUploadKey=(dataset?:number,batch?:number)=>`dataguard:pending-upload:${dataset??'new'}:${batch??'new'}`
export function readPendingUpload(storage:Pick<Storage,'getItem'>,key:string):PendingUpload|null {
  try {
    const value=JSON.parse(storage.getItem(key)??'null') as PendingUpload|null
    return value&&typeof value.filename==='string'&&typeof value.size==='number'&&typeof value.startedAt==='string'&&Array.isArray(value.beforeIds)&&value.beforeIds.every(Number.isSafeInteger)?value:null
  }catch{return null}
}
