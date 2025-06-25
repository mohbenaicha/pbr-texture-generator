import React from 'react';
import { useDropzone } from 'react-dropzone';
import { Box, Typography, Paper } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';

function ImageUploader({ onImageLoaded }) {
  const onDrop = React.useCallback(acceptedFiles => {
    const file = acceptedFiles[0];
    const reader = new FileReader();
    reader.onload = () => {
      onImageLoaded(reader.result);
    };
    reader.readAsDataURL(file);
  }, [onImageLoaded]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept: { 'image/*': [] } });

  return (
    <Paper
      {...getRootProps()}
      sx={{
        p: 2,
        mb: 2,
        textAlign: 'center',
        cursor: 'pointer',
        border: '2px dotted #7F5AF0',
        borderRadius: 4, // 32px
        width: 320,
        height: 320,
        aspectRatio: '1 / 1',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#23242B',
        color: '#A1A1AA',
      }}
      variant="outlined"
    >
      <input {...getInputProps()} />
      <CloudUploadIcon sx={{ fontSize: 56, mb: 1, color: '#7F5AF0' }} />
      <Typography variant="body1">
        {isDragActive ? 'Drop the image here...' : 'Drag & drop an image, or click to select'}
      </Typography>
    </Paper>
  );
}

export default ImageUploader; 