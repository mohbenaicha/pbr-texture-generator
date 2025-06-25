import React, { useState, useImperativeHandle, forwardRef } from 'react';
import { Box, Typography, Slider, Button, MenuItem, Select, InputLabel, FormControl } from '@mui/material';

const splatFiles = [
  'splat1.png','splat2.png','splat3.png','splat4.png','splat5.png','splat6.png','splat7.png','splat8.png','splat9.png','splat10.png','splat11.png','splat12.png','splat13.png','splat14.png','splat15.png','splat16.png','splat17.png','splat18.png','splat19.png','splat20.png','splat21.png','splat22.png'
];

const builtInSplats = [
  { label: 'Standard Brush', value: null },
  ...splatFiles.map((file, idx) => ({ label: `Splat ${idx+1}`, value: `/brushes/${file}` }))
];

const BrushControls = forwardRef(function BrushControls({ brushSize, brushOpacity, brushSplat, onChange, iconButtons, customSplats = [], onAddCustomSplat }, ref) {
  const mode = brushSplat === 'eraser' ? 'eraser' : 'brush';

  // Expose setMode and selectSplat for keyboard shortcuts
  useImperativeHandle(ref, () => ({
    setMode: (newMode) => {
      if (newMode === 'eraser') {
        onChange({ brushSize, brushOpacity, brushSplat: 'eraser' });
      } else {
        onChange({ brushSize, brushOpacity, brushSplat: brushSplat === 'eraser' ? null : brushSplat });
      }
    },
    selectSplat: (index) => {
      const splat = builtInSplats[index - 1];
      if (splat) {
        if (mode === 'brush') {
          onChange({ brushSize, brushOpacity, brushSplat: splat.value });
        }
      }
    }
  }));

  const handleSizeChange = (_, value) => {
    onChange({ brushSize: value, brushOpacity, brushSplat: mode === 'eraser' ? 'eraser' : brushSplat });
  };
  const handleOpacityChange = (_, value) => {
    onChange({ brushSize, brushOpacity: value, brushSplat: mode === 'eraser' ? 'eraser' : brushSplat });
  };
  const handleSplatChange = (e) => {
    if (mode === 'brush') {
      onChange({ brushSize, brushOpacity, brushSplat: e.target.value });
    }
  };
  const handleCustomSplat = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const newSplat = { label: file.name, value: reader.result };
      if (onAddCustomSplat) onAddCustomSplat(newSplat);
      if (mode === 'brush') {
        onChange({ brushSize, brushOpacity, brushSplat: reader.result });
      }
    };
    reader.readAsDataURL(file);
  };

  // Combine built-in and custom splats for the dropdown
  const splatOptions = [...builtInSplats, ...customSplats];

  return (
    <Box sx={{ mb: 2, width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'stretch', px: 2 }}>
      <Box sx={{ display: 'flex', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', mb: 2, gap: 1, flexWrap: 'wrap' }}>
        {iconButtons}
      </Box>
      <Box sx={{ mt: 2, width: '100%' }}>
        <Typography variant="caption" sx={{ display: 'block', mb: 0.5 }}>Size</Typography>
        <Slider min={1} max={1500} value={brushSize} onChange={handleSizeChange} sx={{ width: '100%' }} />
      </Box>
      <Typography variant="caption">Opacity</Typography>
      <Slider min={0.1} max={1} step={0.01} value={brushOpacity} onChange={handleOpacityChange} sx={{ mt: 1, width: '100%' }} />
      {mode === 'brush' && (
        <>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Splat Brush</InputLabel>
            <Select value={brushSplat || ''} label="Splat Brush" onChange={handleSplatChange}>
              {splatOptions.map(splat => (
                <MenuItem key={splat.label} value={splat.value || ''}>{splat.label}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button variant="outlined" component="label" sx={{ mt: 1, width: '100%' }}>
            Upload Custom Splat PNG
            <input type="file" accept="image/png" hidden onChange={handleCustomSplat} />
          </Button>
        </>
      )}
    </Box>
  );
});

export default BrushControls; 