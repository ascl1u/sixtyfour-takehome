import { useEffect } from 'react';
import Sidebar from './components/Sidebar';
import WorkflowCanvas from './components/WorkflowCanvas';
import ConfigModal from './components/ConfigModal';
import ResultsPanel from './components/ResultsPanel';
import { useWorkflowStore } from './store/workflowStore';

function App() {
  const { fetchBlockTypes, fetchFiles, selectedNodeId } = useWorkflowStore();

  useEffect(() => {
    fetchBlockTypes();
    fetchFiles();
  }, [fetchBlockTypes, fetchFiles]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0a0a0f]">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Canvas */}
      <div className="flex-1 relative">
        <WorkflowCanvas />
        
        {/* Empty state */}
        {useWorkflowStore.getState().nodes.length === 0 && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="mb-4 text-6xl opacity-20">🔧</div>
              <h2 className="text-xl font-semibold text-white/30">
                Start Building Your Workflow
              </h2>
              <p className="mt-2 text-sm text-white/20">
                Drag blocks from the sidebar or click them to add
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Config Modal */}
      {selectedNodeId && <ConfigModal />}

      {/* Results Panel */}
      <ResultsPanel />
    </div>
  );
}

export default App;

