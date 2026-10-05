import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import { Layout } from './components/Layout';
import { Home } from './pages/Home';
import { Login } from './pages/Login';
import { CampaignWizard } from './pages/CampaignWizard';
import { CampaignList } from './pages/CampaignList';
import { CampaignDetail } from './pages/CampaignDetail';
import { ApprovalCenter } from './pages/ApprovalCenter';
import { AnalyticsPage } from './pages/Analytics';
import { ApiConsole } from './pages/ApiConsole';
import { Settings } from './pages/Settings';

function ProtectedApp() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/campaigns" element={<CampaignList />} />
        <Route path="/campaigns/new" element={<CampaignWizard />} />
        <Route path="/campaigns/:campaignId" element={<CampaignDetail />} />
        <Route path="/approvals" element={<ApprovalCenter />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/api-console" element={<ApiConsole />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

export default function App() {
  const { token } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/*" element={token ? <ProtectedApp /> : <Navigate to="/login" replace />} />
    </Routes>
  );
}
