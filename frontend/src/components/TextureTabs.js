import React, { forwardRef, useRef, useEffect, useState } from 'react';
import { Tabs, Tab, Box, Typography } from '@mui/material';
import MaskPainter from './MaskPainter';

function TextureTabs({ textures, tab, setTab, textureTypes, originalImage, maskImage, brushSize, brushOpacity, brushSplat, onMaskChange, maskPainterRef, savedMaskData }) {
  const allTabs = ['Original', ...textureTypes];
  const parentRef = useRef();
  const [parentDims, setParentDims] = useState({ width: 0, height: 0 });


  useEffect(() => {
    function updateDims() {
      if (parentRef.current) {
        setParentDims({
          width: parentRef.current.clientWidth,
          height: parentRef.current.clientHeight,
        });
      }
    }
    updateDims();
    window.addEventListener('resize', updateDims);
    return () => window.removeEventListener('resize', updateDims);
  }, []);

  return (
    <Box sx={{ width: '100%', height: '100%' }}>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="scrollable" scrollButtons="auto">
        {allTabs.map((type, idx) => (
          <Tab label={type} key={type} />
        ))}
      </Tabs>
      <Box
        ref={parentRef}
        sx={{
          position: 'relative',
          width: '100%',
          minHeight: 400,
          height: 600,
          overflow: 'hidden',
          display: 'block',
          p: 1,
        }}
      >
        {tab === 0 ? (
          originalImage ? (
            <MaskPainter
              ref={maskPainterRef}
              image={originalImage}
              brushSize={brushSize}
              brushOpacity={brushOpacity}
              brushSplat={brushSplat}
              onMaskChange={onMaskChange}
              maxWidth={parentDims.width - 2 * 8}
              maxHeight={parentDims.height - 2 * 8}
              savedMaskData={savedMaskData}
            />
          ) : (
            <Typography variant="body2" color="text.secondary">
              No original image uploaded yet.
            </Typography>
          )
        ) : (
          textureTypes.map((type, idx2) => (
            tab === idx2 + 1 ? (
              textures[type.toLowerCase()] ? (
                <img
                  key={type}
                  src={textures[type.toLowerCase()].startsWith('data:') ? textures[type.toLowerCase()] : `data:image/png;base64,${textures[type.toLowerCase()]}`}
                  alt={type}
                  style={{ maxWidth: '100%', maxHeight: 400 }}
                />
              ) : (
                <Typography key={type} variant="body2" color="text.secondary">
                  No {type} texture generated yet.
                </Typography>
              )
            ) : null
          ))
        )}
      </Box>
    </Box>
  );
}

export default TextureTabs; 