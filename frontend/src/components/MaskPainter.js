import React, { useEffect, useRef, useState, useImperativeHandle, forwardRef } from 'react';
import { Box } from '@mui/material';
import { Rnd } from 'react-rnd';

function MaskPainter(props, ref) {
  const { image, brushSize, brushOpacity, brushSplat, onMaskChange, maxWidth, maxHeight, savedMaskData } = props;
  const imageCanvasRef = useRef();
  const maskCanvasRef = useRef();
  const [mousePos, setMousePos] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [history, setHistory] = useState([]);
  const [imgDims, setImgDims] = useState({ width: 300, height: 300 });
  const [displayDims, setDisplayDims] = useState({ width: 300, height: 300 });


  // When image loads, get its original dimensions
  useEffect(() => {
    if (!image) return;
    const img = new window.Image();
    img.onload = () => {
      setImgDims({ width: img.width, height: img.height });
      setDisplayDims({ width: Math.max(300, Math.min(500, img.width)), height: Math.max(300, Math.min(500, img.height)) });
    };
    img.src = image;
  }, [image]);

  // Draw the background image on the image canvas
  useEffect(() => {
    const ctx = imageCanvasRef.current.getContext('2d');
    ctx.clearRect(0, 0, imgDims.width, imgDims.height);
    if (image) {
      const img = new window.Image();
      img.onload = () => {
        ctx.drawImage(img, 0, 0, imgDims.width, imgDims.height);
      };
      img.src = image;
    }
  }, [image, imgDims]);

  // Save initial blank mask state for undo when image changes
  useEffect(() => {
    const maskCanvas = maskCanvasRef.current;
    const ctx = maskCanvas.getContext('2d');
    setTimeout(() => {
      const imageData = ctx.getImageData(0, 0, imgDims.width, imgDims.height);
      setHistory([imageData]);
    }, 0);
  }, [image, imgDims]);

  // Simple mask restoration - only run once when component mounts with saved data
  useEffect(() => {
    if (savedMaskData && maskCanvasRef.current) {
      // Add delay to ensure initial setup is complete
      setTimeout(() => {
        const maskCanvas = maskCanvasRef.current;
        const ctx = maskCanvas.getContext('2d');
        const img = new Image();
        img.onload = () => {
          ctx.drawImage(img, 0, 0);
        };
        img.src = savedMaskData;
      }, 20);
    }
  }, []); // Empty dependency array - only run once on mount

  // Painting/erasing logic for the mask canvas
  useEffect(() => {
    const maskCanvas = maskCanvasRef.current;
    const ctx = maskCanvas.getContext('2d');
    let drawing = false;

    const getBrush = () => {
      if (brushSplat && brushSplat !== 'eraser') {
        const img = new window.Image();
        img.src = brushSplat;
        return img;
      }
      return null;
    };

    let brushImg = getBrush();

    const draw = (x, y, mode) => {
      if (brushSplat && brushSplat !== 'eraser' && brushImg && brushImg.complete) {
        ctx.save();
        ctx.globalAlpha = brushOpacity;
        ctx.globalCompositeOperation = 'source-over';
        ctx.drawImage(brushImg, x - brushSize / 2, y - brushSize / 2, brushSize, brushSize);
        ctx.restore();
      } else {
        ctx.save();
        ctx.globalAlpha = brushOpacity;
        ctx.globalCompositeOperation = mode === 'eraser' ? 'destination-out' : 'source-over';
        ctx.beginPath();
        ctx.arc(x, y, brushSize / 2, 0, 2 * Math.PI);
        ctx.fillStyle = mode === 'eraser' ? 'rgba(0,0,0,1)' : `rgba(0,0,0,${brushOpacity})`;
        ctx.fill();
        ctx.restore();
      }
    };

    const handlePointerDown = (e) => {
      // Save state before drawing
      const ctx = maskCanvas.getContext('2d');
      const imageData = ctx.getImageData(0, 0, imgDims.width, imgDims.height);
      setHistory(prev => [...prev, imageData]);
      drawing = true;
      setIsDrawing(true);
      const rect = maskCanvas.getBoundingClientRect();
      // Map to original image coordinates
      const x = ((e.clientX - rect.left) / rect.width) * imgDims.width;
      const y = ((e.clientY - rect.top) / rect.height) * imgDims.height;
      draw(x, y, brushSplat === 'eraser' ? 'eraser' : 'brush');
    };
    const handlePointerMove = (e) => {
      const rect = maskCanvas.getBoundingClientRect();
      // Map to original image coordinates
      const x = ((e.clientX - rect.left) / rect.width) * imgDims.width;
      const y = ((e.clientY - rect.top) / rect.height) * imgDims.height;
      setMousePos({ x, y });
      if (!drawing) return;
      draw(x, y, brushSplat === 'eraser' ? 'eraser' : 'brush');
    };
    const handlePointerUp = () => {
      drawing = false;
      setIsDrawing(false);
      if (onMaskChange) {
        const maskData = maskCanvas.toDataURL('image/png');
        onMaskChange(maskData);
      }
    };
    maskCanvas.addEventListener('pointerdown', handlePointerDown);
    maskCanvas.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp);
    return () => {
      maskCanvas.removeEventListener('pointerdown', handlePointerDown);
      maskCanvas.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };
    // eslint-disable-next-line
  }, [brushSize, brushOpacity, brushSplat, onMaskChange, imgDims]);

  // Undo function
  useImperativeHandle(ref, () => ({
    undoMask: () => {
      if (history.length === 0) return;
      const maskCanvas = maskCanvasRef.current;
      const ctx = maskCanvas.getContext('2d');
      const newHistory = [...history];
      const last = newHistory.pop();
      if (last) {
        ctx.putImageData(last, 0, 0);
        if (onMaskChange) {
          const maskData = maskCanvas.toDataURL('image/png');
          onMaskChange(maskData);
        }
        setHistory(newHistory);
      }
    }
  }), [history, onMaskChange]);

  // Brush preview overlay (always visible under cursor)
  return (
    <Rnd
      size={{ width: displayDims.width, height: displayDims.height }}
      minWidth={150}
      minHeight={150}
      maxWidth={maxWidth || imgDims.width}
      maxHeight={maxHeight || imgDims.height}
      bounds="parent"
      onResize={(e, direction, ref, delta, position) => {
        setDisplayDims({ width: ref.offsetWidth, height: ref.offsetHeight });
      }}
      style={{ marginBottom: 16 }}
      disableDragging
      enableResizing={{
        bottom: true,
        bottomRight: true,
        right: true,
      }}
      resizeHandleStyles={{
        right: { width: '16px', background: 'rgba(127,90,240,0.2)', cursor: 'ew-resize' },
        bottom: { height: '16px', background: 'rgba(127,90,240,0.2)', cursor: 'ns-resize' },
        bottomRight: { width: '24px', height: '24px', background: 'rgba(127,90,240,0.3)', cursor: 'nwse-resize' },
      }}
    >
      <Box sx={{ width: '100%', height: '100%', border: '1px solid #ccc', position: 'relative' }}>
        {/* Background image layer */}
        <canvas
          ref={imageCanvasRef}
          width={imgDims.width}
          height={imgDims.height}
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            zIndex: 1,
            width: '100%',
            height: '100%',
            imageRendering: 'auto',
          }}
        />
        {/* Mask layer */}
        <canvas
          ref={maskCanvasRef}
          width={imgDims.width}
          height={imgDims.height}
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            zIndex: 2,
            width: '100%',
            height: '100%',
            imageRendering: 'auto',
          }}
          onMouseLeave={() => setMousePos(null)}
          onMouseEnter={e => {
            const rect = e.currentTarget.getBoundingClientRect();
            // Map to original image coordinates
            setMousePos({
              x: ((e.nativeEvent.clientX - rect.left) / rect.width) * imgDims.width,
              y: ((e.nativeEvent.clientY - rect.top) / rect.height) * imgDims.height,
            });
          }}
        />
        {/* Brush preview overlay */}
        {mousePos && (
          <Box
            sx={{
              pointerEvents: 'none',
              position: 'absolute',
              left: 0,
              top: 0,
              width: '100%',
              height: '100%',
              zIndex: 3,
            }}
          >
            {brushSplat && brushSplat !== 'eraser' ? (
              <img
                src={brushSplat}
                alt="brush preview"
                style={{
                  position: 'absolute',
                  left: (mousePos.x / imgDims.width) * displayDims.width - (brushSize * (displayDims.width / imgDims.width)) / 2,
                  top: (mousePos.y / imgDims.height) * displayDims.height - (brushSize * (displayDims.height / imgDims.height)) / 2,
                  width: brushSize * (displayDims.width / imgDims.width),
                  height: brushSize * (displayDims.height / imgDims.height),
                  opacity: brushOpacity,
                  pointerEvents: 'none',
                  filter: 'drop-shadow(0 0 4px #000a)',
                }}
              />
            ) : (
              <div
                style={{
                  position: 'absolute',
                  left: (mousePos.x / imgDims.width) * displayDims.width - (brushSize * (displayDims.width / imgDims.width)) / 2,
                  top: (mousePos.y / imgDims.height) * displayDims.height - (brushSize * (displayDims.height / imgDims.height)) / 2,
                  width: brushSize * (displayDims.width / imgDims.width),
                  height: brushSize * (displayDims.height / imgDims.height),
                  borderRadius: '50%',
                  border: brushSplat === 'eraser' ? '3px solid #ff3b3b' : '3px solid #7F5AF0',
                  background: brushSplat === 'eraser'
                    ? 'rgba(255,0,0,0.3)'
                    : 'rgba(0,0,0,0.3)',
                  outline: '1.5px solid #fff2',
                  pointerEvents: 'none',
                  boxShadow: '0 0 6px #000a',
                }}
              />
            )}
          </Box>
        )}
      </Box>
    </Rnd>
  );
}

export default forwardRef(MaskPainter); 