export type PartListItem = { part_id: string; status: string; created_at: string; finished_at: string | null }

export type MachineLive = {
  machine: string
  machine_name: string
  nominal_duration_s: number
  last_ts: string | null
  last_part_id: string | null
  last_level: string | null
  last_code: string | null
  last_message: string | null
  last_cycle: number | null
  last_step_id: string | null
  last_step_name: string | null
  last_duration: number | null
  last_payload: any
}

export type PartStep = {
  part_id: string
  machine: string
  step_id: string
  step_name: string
  cycle: number
  start_time: string
  end_time: string
  real_duration_s: number
}

export type PartMachineCycle = {
  machine: string
  cycle: number
  real_cycle_time_s: number
  nominal_duration_s: number
  delta_s: number
  status: string
}

export type WorkorderListItem = {
  id : string
  name: string
  status: string
  // todo 
}

export type PartDetail = { part_id: string; machines: PartMachineCycle[]; steps: PartStep[] }
