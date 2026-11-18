// Espelha app/schemas/employee.py::EmployeePublic (backend)
export interface Employee {
  id: number
  store_id: number
  sector_id: number
  name: string
  role_title: string | null
  active: boolean
  has_pin: boolean
}
