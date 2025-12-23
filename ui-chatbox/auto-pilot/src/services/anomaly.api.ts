import axios from 'axios'

export async function getAnomalies(page: number, pageSize: number) {
  const res = await axios.get('/api/anomalies', {
    params: { page, page_size: pageSize }
  })
  return res.data
}

export async function getAnomalyCycle(id: string) {
  const res = await axios.get(`/api/anomalies/${id}/cycle`)
  return res.data
}