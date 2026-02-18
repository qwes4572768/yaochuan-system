import { BrowserRouter, Routes, Route, NavLink, useNavigate, useParams } from 'react-router-dom'
import logoUrl from './assets/brand-logo.png'
import { AuthProvider, useAuth } from './auth/AuthProvider'
import { ProtectedRoute } from './auth/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import EmployeeList from './pages/EmployeeList'
import EmployeeForm from './pages/EmployeeForm'
import EmployeeDetail from './pages/EmployeeDetail'
import Reports from './pages/Reports'
import RateTables from './pages/RateTables'
import BracketImport from './pages/BracketImport'
import BackupRestore from './pages/BackupRestore'
import SiteList from './pages/SiteList'
import SiteForm from './pages/SiteForm'
import SiteDetail from './pages/SiteDetail'
import SiteHistory from './pages/SiteHistory'
import SecurityPayroll from './pages/SecurityPayroll'
import PatrolBindPage from './pages/PatrolBindPage'
import PatrolPage from './pages/PatrolPage'
import PatrolPublicCheckinPage from './pages/PatrolPublicCheckinPage'
import PatrolBindingAdminPage from './pages/PatrolBindingAdminPage'
import PatrolBindingLegacyPage from './pages/PatrolBindingLegacyPage'
import PatrolPointsPage from './pages/PatrolPointsPage'
import PatrolLogsPage from './pages/PatrolLogsPage'

function PatrolPublicCheckinRoute() {
  const { publicId = '' } = useParams()
  return <PatrolPublicCheckinPage publicId={publicId} />
}

function LogoutButton() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  return (
    <button
      type="button"
      onClick={() => {
        logout()
        navigate('/login', { replace: true })
      }}
      className="px-3 py-1.5 rounded hover:bg-slate-700 text-slate-200"
    >
      登出
    </button>
  )
}

function AppLayout() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-slate-800 text-white shadow min-h-20 flex items-center py-4">
        <div className="max-w-6xl mx-auto px-4 w-full flex items-center justify-between gap-4">
          <NavLink to="/" className="flex items-center gap-2 whitespace-nowrap shrink-0">
            <img
              src={logoUrl}
              alt="懶人管理系統"
              className="h-16 md:h-20 w-auto max-w-[360px] md:max-w-[520px] object-contain shrink-0 select-none"
            />
          </NavLink>
          <nav className="flex gap-4 flex-wrap items-center justify-end min-w-0">
              <NavLink
                to="/"
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded ${isActive ? 'bg-slate-600' : 'hover:bg-slate-700'}`
                }
              >
                員工清單
              </NavLink>
              <NavLink
                to="/employees/new"
                className="px-3 py-1.5 rounded hover:bg-slate-700"
              >
                新增員工
              </NavLink>
              <NavLink
                to="/reports"
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded ${isActive ? 'bg-slate-600' : 'hover:bg-slate-700'}`
                }
              >
                報表匯出
              </NavLink>
              <NavLink
                to="/rate-tables"
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded ${isActive ? 'bg-slate-600' : 'hover:bg-slate-700'}`
                }
              >
                級距費率
              </NavLink>
              <NavLink
                to="/bracket-import"
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded ${isActive ? 'bg-slate-600' : 'hover:bg-slate-700'}`
                }
              >
                級距表匯入
              </NavLink>
              <NavLink
                to="/backup-restore"
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded ${isActive ? 'bg-slate-600' : 'hover:bg-slate-700'}`
                }
              >
                備份還原
              </NavLink>
              <NavLink
                to="/sites"
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded ${isActive ? 'bg-slate-600' : 'hover:bg-slate-700'}`
                }
              >
                案場管理
              </NavLink>
              <NavLink
                to="/accounting/security-payroll"
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded ${isActive ? 'bg-slate-600' : 'hover:bg-slate-700'}`
                }
              >
                傻瓜會計
              </NavLink>
              <NavLink
                to="/patrol-admin/bindings"
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded ${isActive ? 'bg-slate-600' : 'hover:bg-slate-700'}`
                }
              >
                永久巡邏點 QR
              </NavLink>
              <NavLink
                to="/patrol-admin/points"
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded ${isActive ? 'bg-slate-600' : 'hover:bg-slate-700'}`
                }
              >
                巡邏點管理
              </NavLink>
              <NavLink
                to="/patrol-admin/logs"
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded ${isActive ? 'bg-slate-600' : 'hover:bg-slate-700'}`
                }
              >
                巡邏紀錄
              </NavLink>
              <LogoutButton />
            </nav>
          </div>
        </header>
        <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<EmployeeList />} />
            <Route path="/employees/new" element={<EmployeeForm />} />
            <Route path="/employees/:id" element={<EmployeeDetail />} />
            <Route path="/employees/:id/edit" element={<EmployeeForm />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/rate-tables" element={<RateTables />} />
            <Route path="/bracket-import" element={<BracketImport />} />
            <Route path="/backup-restore" element={<BackupRestore />} />
            <Route path="/sites" element={<SiteList />} />
            <Route path="/sites/history" element={<SiteHistory />} />
            <Route path="/sites/new" element={<SiteForm />} />
            <Route path="/sites/:id" element={<SiteDetail />} />
            <Route path="/sites/:id/edit" element={<SiteForm />} />
            <Route path="/accounting/security-payroll" element={<SecurityPayroll />} />
            <Route path="/patrol-admin/bindings" element={<PatrolBindingAdminPage />} />
            <Route path="/patrol-admin/bindings/legacy" element={<PatrolBindingLegacyPage />} />
            <Route path="/patrol-admin/points" element={<PatrolPointsPage />} />
            <Route path="/patrol-admin/logs" element={<PatrolLogsPage />} />
          </Routes>
        </main>
      </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/patrol/bind" element={<PatrolBindPage />} />
          <Route path="/patrol/checkin/:publicId" element={<PatrolPublicCheckinRoute />} />
          <Route path="/patrol" element={<PatrolPage />} />
          <Route path="*" element={<ProtectedRoute><AppLayout /></ProtectedRoute>} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
