// src/components/SidePanel.jsx
import { useContext, useState } from 'react';
import { GameContext } from '../context/GameContext';
import MachineControls from './MachineControls';
import ViewCreaturesButton from './ViewCreaturesButton';
import CreaturesViewer from './CreaturesViewer';

const SidePanel = ({ isOpen }) => {
  const { 
    userName,
    tcorvax,
    catNips,
    energy,
    eggs,
    formatResource,
    isMobile 
  } = useContext(GameContext);
  
  // Add state for creatures viewer visibility
  const [showCreaturesViewer, setShowCreaturesViewer] = useState(false);

  return (
    <>
      <div
        className={`side-panel ${isOpen ? 'open' : ''}`}
        style={{
          position: isMobile ? 'fixed' : 'relative',
          width: isMobile ? '100%' : '300px',
          height: isMobile ? 'calc(100vh - 50px)' : '100vh',
          background: 'rgba(30, 30, 30, 0.95)',
          boxShadow: '0 0 15px rgba(76, 175, 80, 0.3)',
          backdropFilter: 'blur(10px)',
          borderRadius: '0 10px 10px 0',
          transition: 'transform 0.3s ease',
          transform: isMobile && !isOpen ? 'translateX(-100%)' : 'translateX(0)',
          zIndex: isMobile ? 100 : 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          paddingBottom: '80px'
        }}
      >
        <div className="panel-user-container">
          <div className="user-info">
            <h2>Welcome, {userName}</h2>
          </div>
        </div>

        {/* Resource display section */}
        <div className="resources-container">
          <div className="resource">
            <div className="resource-icon">💎</div>
            <div className="resource-value">{formatResource(tcorvax)}</div>
            <div className="resource-name">TCorvax</div>
          </div>
          <div className="resource">
            <div className="resource-icon">🐱</div>
            <div className="resource-value">{formatResource(catNips)}</div>
            <div className="resource-name">CatNips</div>
          </div>
          <div className="resource">
            <div className="resource-icon">⚡</div>
            <div className="resource-value">{formatResource(energy)}</div>
            <div className="resource-name">Energy</div>
          </div>
          <div className="resource">
            <div className="resource-icon">🥚</div>
            <div className="resource-value">{formatResource(eggs)}</div>
            <div className="resource-name">Eggs</div>
          </div>
        </div>
        
        {/* Add the ViewCreaturesButton component before MachineControls */}
        <ViewCreaturesButton onClick={() => setShowCreaturesViewer(true)} />
        
        <MachineControls />
      </div>
      
      {/* Render the CreaturesViewer when showCreaturesViewer is true */}
      {showCreaturesViewer && (
        <CreaturesViewer onClose={() => setShowCreaturesViewer(false)} />
      )}
    </>
  );
};

export default SidePanel;
