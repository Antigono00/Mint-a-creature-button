// src/components/ViewCreaturesButton.jsx
import { useContext } from 'react';
import { GameContext } from '../context/GameContext';
import { useRadixConnect } from '../context/RadixConnectContext';

const ViewCreaturesButton = ({ onClick }) => {
  // From the GameContext
  const { isMobile } = useContext(GameContext);
  
  // From the RadixConnect context
  const { connected, accounts } = useRadixConnect();

  // Simple button styles based on connected status
  const isConnected = connected && accounts && accounts.length > 0;
  
  return (
    <div style={{ marginBottom: '15px', textAlign: 'center' }}>
      <button
        onClick={onClick}
        className="view-creatures-button"
        style={{
          backgroundColor: isConnected ? '#4CAF50' : '#666',
          color: 'white',
          padding: '8px 15px',
          borderRadius: '6px',
          border: 'none',
          cursor: isConnected ? 'pointer' : 'not-allowed',
          fontSize: '14px',
          fontWeight: 'bold',
          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px',
          margin: '0 auto',
          opacity: isConnected ? 1 : 0.7
        }}
        disabled={!isConnected}
      >
        <span role="img" aria-label="view creatures">🔍</span> View Creatures
      </button>
      
      {!isConnected && (
        <p style={{ 
          fontSize: '11px', 
          marginTop: '5px', 
          color: '#999', 
          textAlign: 'center' 
        }}>
          Connect wallet to view your creatures
        </p>
      )}
    </div>
  );
};

export default ViewCreaturesButton;
