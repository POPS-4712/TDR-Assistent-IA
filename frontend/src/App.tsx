import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './pages/Dashboard';
import { Automations } from './pages/Automations';
import { Accounts } from './pages/Accounts';
import { System } from './pages/System';
import { Executions } from './pages/Executions';
import { Profiles } from './pages/Profiles/Profiles';

function App() {
  return (
    <Router>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/profiles" element={<Profiles />} />
          <Route path="/automations" element={<Automations />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/system" element={<System />} />
          <Route path="/executions" element={<Executions />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
