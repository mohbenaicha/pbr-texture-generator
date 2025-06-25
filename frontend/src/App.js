import React, { useState, useRef } from 'react';
import { Box, Button, TextField, Tabs, Tab, Typography, Card, CardContent, IconButton, Tooltip, useTheme, createTheme, ThemeProvider } from '@mui/material';
import BrushIcon from '@mui/icons-material/Brush';
import UndoIcon from '@mui/icons-material/Undo';
import EditIcon from '@mui/icons-material/Edit';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import AutoFixOffIcon from '@mui/icons-material/AutoFixOff';
import ImageUploader from './components/ImageUploader';
import MaskPainter from './components/MaskPainter';
import BrushControls from './components/BrushControls';
import TextureTabs from './components/TextureTabs';
import axios from 'axios';
import Snackbar from '@mui/material/Snackbar';
import CloseIcon from '@mui/icons-material/Close';
import RefreshIcon from '@mui/icons-material/Refresh';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';

const textureTypes = ['Albedo', 'Normal', 'Rough', 'Metal', 'Height', 'AmbientOcl', 'Specular'];

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    background: { default: '#181A20', paper: '#23242B' },
    primary: { main: '#7F5AF0' },
    secondary: { main: '#2CB67D' },
    text: { primary: '#F5F7FA', secondary: '#A1A1AA' },
  },
  typography: {
    fontFamily: 'Inter, Roboto, Arial, sans-serif',
    fontSize: 13,
  },
  shape: {
    borderRadius: 4,
  },
});

function App() {
  const [image, setImage] = useState(null);
  const [mask, setMask] = useState(null);
  const [prompt, setPrompt] = useState('');
  const [textures, setTextures] = useState({});
  const [tab, setTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [brushSize, setBrushSize] = useState(10);
  const [brushOpacity, setBrushOpacity] = useState(1);
  const [brushSplat, setBrushSplat] = useState(null);
  const [lastUsedBrushSplat, setLastUsedBrushSplat] = useState(null); // Track last used brush (null or splat, never 'eraser')
  const lastUsedBrushSplatRef = useRef(lastUsedBrushSplat);
  const [editTab, setEditTab] = useState(1); // 0: Upload, 1: Edit
  const [inputFocused, setInputFocused] = useState(false);
  const [showUploadSuccess, setShowUploadSuccess] = useState(false);
  const [showRemoveDialog, setShowRemoveDialog] = useState(false);
  const [showRefreshDialog, setShowRefreshDialog] = useState(false);
  const [shortcutTriggeredDialog, setShortcutTriggeredDialog] = useState(null); // Track if dialog was triggered by shortcut
  const [customSplats, setCustomSplats] = useState([]); // [{ label, value }]
  const [shortcutUsed, setShortcutUsed] = useState(null); // Track which shortcut was used for visual feedback
  const maskPainterRef = useRef();
  const brushControlsRef = useRef();
  const savedMaskDataRef = useRef(null);

  // Debug useEffect to track lastUsedBrushSplat changes
  React.useEffect(() => {
  }, [lastUsedBrushSplat]);

  // Keyboard shortcuts
  React.useEffect(() => {
    const handleKeyDown = (e) => {
      if (inputFocused) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        if (maskPainterRef.current && maskPainterRef.current.undoMask) maskPainterRef.current.undoMask();
      } else if (e.key.toLowerCase() === 'b') {
        e.preventDefault();
        setShortcutUsed('brush');
        setTimeout(() => setShortcutUsed(null), 200);
        setBrushSplat(lastUsedBrushSplatRef.current);
      } else if (e.key.toLowerCase() === 'e') {
        e.preventDefault();
        setShortcutUsed('eraser');
        setTimeout(() => setShortcutUsed(null), 200);
        setBrushSplat('eraser');
      } else if (e.key.toLowerCase() === 'x') {
        e.preventDefault();
        setShortcutUsed('remove');
        setTimeout(() => setShortcutUsed(null), 200);
        setShortcutTriggeredDialog('remove');
        setShowRemoveDialog(true);
      } else if (e.key.toLowerCase() === 'r') {
        e.preventDefault();
        setShortcutUsed('refresh');
        setTimeout(() => setShortcutUsed(null), 200);
        setShortcutTriggeredDialog('refresh');
        setShowRefreshDialog(true);
      } else if (/^[1-9]$/.test(e.key)) {
        if (brushControlsRef.current && brushControlsRef.current.selectSplat) brushControlsRef.current.selectSplat(Number(e.key));
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [inputFocused]);

  const handleBrushChange = ({ brushSize, brushOpacity, brushSplat, mode, splatIndex }) => {
    if (brushSize !== undefined) setBrushSize(brushSize);
    if (brushOpacity !== undefined) setBrushOpacity(brushOpacity);
    if (brushSplat !== undefined) {
      setBrushSplat(brushSplat);
      if (brushSplat !== null && brushSplat !== 'eraser') {
        setLastUsedBrushSplat(brushSplat);
        lastUsedBrushSplatRef.current = brushSplat;
      }
    }
  };

  const handleMaskChange = (maskData) => {
    setMask(maskData);
    savedMaskDataRef.current = maskData;
  };

  // Function to download base64 data as PNG file
  const downloadBase64AsPNG = (base64Data, filename) => {
    if (!base64Data) return;
    
    // Remove data URL prefix if present
    const base64String = base64Data.replace(/^data:image\/[a-z]+;base64,/, '');
    
    // Create blob and download link
    const byteCharacters = atob(base64String);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: 'image/png' });
    
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleGenerate = async () => {
    setLoading(true);
    try {
      // Invert the mask before sending to backend
      let invertedMask = mask;
      if (mask) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        // Make it synchronous
        await new Promise((resolve) => {
          img.onload = () => {
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const data = imageData.data;
            // Invert the mask (black becomes white, white becomes black)
            for (let i = 0; i < data.length; i += 4) {
              data[i] = 255 - data[i];     // Red
              data[i + 1] = 255 - data[i + 1]; // Green
              data[i + 2] = 255 - data[i + 2]; // Blue
              // Alpha stays the same
            }
            ctx.putImageData(imageData, 0, 0);
            invertedMask = canvas.toDataURL('image/png');
            resolve();
          };
          img.src = mask;
        });
      }

      const response = await axios.post("http://127.0.0.1:5000/generate-textures/", {
        user_image: image,
        user_mask: invertedMask,
        prompt,
        batch: false,
      });
      setTextures(response.data);
    } catch (err) {
      alert("Error generating textures");
    }
    setLoading(false);
  };

  const handleUndo = () => {
    if (maskPainterRef.current && maskPainterRef.current.undoMask) {
      maskPainterRef.current.undoMask();
    }
  };

  // Image upload handler with confirmation
  const handleImageUpload = (img) => {
    setImage(img);
    setShowUploadSuccess(true);
  };

  // Brush/Eraser icon click handlers
  const handleBrushIconClick = () => {
    if (brushSplat !== lastUsedBrushSplat) {
      // setBrushSplat(lastUsedBrushSplatRef.current);
      brushControlsRef.current?.setMode('brush');
      setBrushSplat(lastUsedBrushSplatRef.current);
      brushControlsRef.current?.onChange?.({ brushSize, brushOpacity, brushSplat: lastUsedBrushSplatRef.current });    }
  };
  const handleEraserIconClick = () => {
    if (brushSplat !== 'eraser') {
      setBrushSplat('eraser');
      brushControlsRef.current?.setMode('eraser');
      brushControlsRef.current?.onChange?.({ brushSize, brushOpacity, brushSplat: 'eraser' });
    }
  };

  const handleConfirmRemove = () => { 
    setImage(null); 
    setMask(null); 
    setShowRemoveDialog(false); 
    setShortcutTriggeredDialog(null);
  };
  const handleCancelRemove = () => { 
    setShowRemoveDialog(false); 
    setShortcutTriggeredDialog(null);
  };
  const handleConfirmRefresh = () => {
    setImage(null);
    setMask(null);
    setPrompt('');
    setTextures({});
    setTab(0);
    setShowRefreshDialog(false);
    setShortcutTriggeredDialog(null);
    savedMaskDataRef.current = null;
  };
  const handleCancelRefresh = () => { 
    setShowRefreshDialog(false); 
    setShortcutTriggeredDialog(null);
  };

  // Handler to add a custom splat
  const handleAddCustomSplat = (splat) => {
    setCustomSplats(prev => [...prev, splat]);
  };

  return (
    <ThemeProvider theme={darkTheme}>
      <Box minHeight="100vh" bgcolor="background.default" color="text.primary" display="flex" flexDirection="column" alignItems="center" p={3}>
        <Typography
        
          variant="h4"
          fontWeight={900}
          letterSpacing={2}
          mb={2}
          color="primary"
          sx={{ textShadow: '0 2px 8px #000a', textAlign: 'center', fontFamily: 'Montserrat, Inter, Roboto, Arial, sans-serif' }}
        >
          PBR Inpainter
        </Typography>
        <Box display="flex" width="100%" gap={3}>
          <Card
            sx={{
              flex: '1 1 400px',
              minWidth: 200,
              maxWidth: 420,
              bgcolor: 'background.paper',
              p: 2,
              borderRadius: 2,
              boxShadow: 4,
            }}
          >
            <Tabs value={editTab} onChange={(_, v) => setEditTab(v)} variant="fullWidth" sx={{ mb: 2 }}>
              <Tab icon={<UploadFileIcon />} label="Upload" />
              <Tab icon={<EditIcon />} label="Edit Mask" />
            </Tabs>
            <CardContent sx={{ p: 0 }}>
              {editTab === 0 && (
                <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" minHeight={340}>
                  <ImageUploader onImageLoaded={handleImageUpload} dragAreaStyle={{ border: '2px dashed #7F5AF0', borderRadius: 16, background: '#23242B', color: '#A1A1AA', minHeight: 220, width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }} />
                </Box>
              )}
              {editTab === 1 && (
                <Box display="flex" flexDirection="row" alignItems="flex-start" gap={2}>
                  <BrushControls
                    ref={brushControlsRef}
                    brushSize={brushSize}
                    brushOpacity={brushOpacity}
                    brushSplat={brushSplat}
                    onChange={handleBrushChange}
                    customSplats={customSplats}
                    onAddCustomSplat={handleAddCustomSplat}r
                    iconButtons={
                      <>
                        <Tooltip title="Brush (B)"><IconButton color={(brushSplat === null || shortcutUsed === 'brush') ? 'primary' : 'default'} onClick={handleBrushIconClick}><BrushIcon /></IconButton></Tooltip>
                        <Tooltip title="Eraser (E)"><IconButton color={(brushSplat === 'eraser' || shortcutUsed === 'eraser') ? 'primary' : 'default'} onClick={handleEraserIconClick}><AutoFixOffIcon /></IconButton></Tooltip>
                        <Tooltip title="Undo (Ctrl+Z)"><IconButton onClick={handleUndo}><UndoIcon /></IconButton></Tooltip>
                        <Tooltip title="Remove Image (X)"><IconButton color={shortcutUsed === 'remove' ? 'primary' : 'default'} onClick={() => setShowRemoveDialog(true)}><CloseIcon /></IconButton></Tooltip>
                        <Tooltip title="Reset Workspace (R)"><IconButton color={shortcutUsed === 'refresh' ? 'primary' : 'default'} onClick={() => setShowRefreshDialog(true)}><RefreshIcon /></IconButton></Tooltip>
                      </>
                    }
                  />
                </Box>
              )}
            </CardContent>
            <Box mt={2} sx={{ px: 2 }}>
              <Typography variant="caption" color="text.secondary" mb={0.5} sx={{ display: 'block' }}>Prompt</Typography>
              <TextField
                value={prompt}
                onChange={e => setPrompt(e.target.value)}
                onFocus={() => setInputFocused(true)}
                onBlur={() => setInputFocused(false)}
                multiline
                minRows={5}
                maxRows={8}
                fullWidth
                variant="outlined"
                size="small"
                sx={{ fontSize: 13, background: '#0000', borderRadius: 0, color: 'text.primary', fontFamily: 'inherit', p: 0.5, mb: 1 }}
                inputProps={{ style: { fontSize: 13, lineHeight: 1.3, padding: 4 } }}
              />
              <Button variant="contained" color="primary" onClick={handleGenerate} disabled={loading} fullWidth sx={{ mt: 2, borderRadius: 2, fontWeight: 600 }}>
                {loading ? 'Generating...' : 'Generate Textures'}
              </Button>
            </Box>
          </Card>
          <Card
            sx={{
              flex: '2 1 800px',
              minWidth: 400,
              maxWidth: 1200,
              bgcolor: 'background.paper',
              p: 2,
              pr: 2,
              borderRadius: 2,
              boxShadow: 4,
              minHeight: 400,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'stretch',
              justifyContent: 'flex-start',
              overflow: 'hidden',
            }}
          >
            <TextureTabs
              textures={textures}
              tab={tab}
              setTab={(newTab) => {
                setTab(newTab);
              }}
              textureTypes={textureTypes}
              originalImage={image}
              maskImage={mask}
              brushSize={brushSize}
              brushOpacity={brushOpacity}
              brushSplat={brushSplat}
              onMaskChange={handleMaskChange}
              maskPainterRef={maskPainterRef}
              savedMaskData={savedMaskDataRef.current}
            />
          </Card>
        </Box>
        <Dialog open={showRemoveDialog} onClose={handleCancelRemove}>
          <DialogTitle>Remove Image?</DialogTitle>
          <DialogContent>
            <DialogContentText>This will remove the current image and mask. Are you sure?</DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCancelRemove}>Cancel</Button>
            <Button onClick={handleConfirmRemove} color="error">Remove</Button>
          </DialogActions>
        </Dialog>
        <Dialog open={showRefreshDialog} onClose={handleCancelRefresh}>
          <DialogTitle>Clear Workspace?</DialogTitle>
          <DialogContent>
            <DialogContentText>This will clear the prompt, all images, and all generated textures. Are you sure?</DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCancelRefresh}>Cancel</Button>
            <Button onClick={handleConfirmRefresh} color="error">Clear</Button>
          </DialogActions>
        </Dialog>
        <Snackbar
          open={showUploadSuccess}
          autoHideDuration={2000}
          onClose={() => setShowUploadSuccess(false)}
          message="Image uploaded successfully!"
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        />
      </Box>
    </ThemeProvider>
  );
}

export default App; 