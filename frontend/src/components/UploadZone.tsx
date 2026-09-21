import React, { useState, useRef } from 'react';
import { DrawingFile } from '../types/comparison';

import { API_CONFIG } from '../config/api';
import { formatBytes } from '../services/comparisonService';
import {
  UploadCloud,
  FileCode,
  FileCheck,
  X,
  ArrowRight,
  Sparkles,
  AlertCircle,
  FileText,
  Layers,
} from 'lucide-react';

interface UploadZoneProps {
  onStartComparison: (
    oldFile: Partial<DrawingFile> | File,
    newFile: Partial<DrawingFile> | File,
    simulatedError?: '422_ALIGNMENT_FAILED' | '500_SERVER_ERROR' | 'NETWORK_TIMEOUT' | null
  ) => void;
  isComparing?: boolean;
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onStartComparison, isComparing = false }) => {
  const [oldDrawing, setOldDrawing] = useState<Partial<DrawingFile> | null>(null);
  const [newDrawing, setNewDrawing] = useState<Partial<DrawingFile> | null>(null);
  const [oldFileObj, setOldFileObj] = useState<File | null>(null);
  const [newFileObj, setNewFileObj] = useState<File | null>(null);

  const [selectedErrorSimulation, setSelectedErrorSimulation] = useState<
    '422_ALIGNMENT_FAILED' | '500_SERVER_ERROR' | 'NETWORK_TIMEOUT' | null
  >(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const oldFileInputRef = useRef<HTMLInputElement>(null);
  const newFileInputRef = useRef<HTMLInputElement>(null);

  const [isDraggingOld, setIsDraggingOld] = useState(false);
  const [isDraggingNew, setIsDraggingNew] = useState(false);



  const validateFile = (file: File): { valid: boolean; error?: string } => {
    // Check file size
    if (file.size > API_CONFIG.maxFileSizeBytes) {
      return {
        valid: false,
        error: `File "${file.name}" exceeds maximum allowed limit (${formatBytes(API_CONFIG.maxFileSizeBytes)}).`,
      };
    }

    // Check extension
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    const isExtensionSupported = API_CONFIG.supportedExtensions.some(
      (e) => e.toLowerCase() === ext
    );

    if (!isExtensionSupported && !file.type.startsWith('image/')) {
      return {
        valid: false,
        error: `Unsupported file format "${ext}". Please provide PDF, DWG, DXF, SVG, PNG, or TIFF files.`,
      };
    }

    return { valid: true };
  };

  const handleFileDrop = (file: File, isOld: boolean) => {
    setValidationError(null);
    const validation = validateFile(file);
    if (!validation.valid) {
      setValidationError(validation.error || 'Invalid file');
      return;
    }

    const drawingData: Partial<DrawingFile> = {
      id: `upload-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      name: file.name,
      revision: isOld ? 'Rev A (Baseline)' : 'Rev B (Incoming)',
      fileSize: formatBytes(file.size),
      dimensions: 'Auto-detecting (Vector/CAD)',
      type: file.name.split('.').pop()?.toLowerCase() || 'cad',
      uploadedAt: new Date().toLocaleTimeString(),
      author: 'Uploaded by Client',
    };

    if (isOld) {
      setOldDrawing(drawingData);
      setOldFileObj(file);
    } else {
      setNewDrawing(drawingData);
      setNewFileObj(file);
    }
  };

  // Button is only clickable when user has put both images and AI is not currently running
  const isReadyToCompare = Boolean(oldFileObj && newFileObj && !isComparing);

  const handleExecuteComparison = () => {
    if (oldFileObj && newFileObj && !isComparing) {
      onStartComparison(oldFileObj, newFileObj, selectedErrorSimulation);
    }
  };

  return (
    <div id="upload-screen-container" className="w-full max-w-5xl mx-auto py-8 px-4">
      {/* Hero Header */}
      <div className="text-center max-w-3xl mx-auto mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#FAFAFA] border border-[#E5E5E5] text-xs text-[#525252] mb-4">
          <Layers className="w-3.5 h-3.5 text-[#0A0A0A]" />
          <span className="font-medium text-xs">CAD & Vector Comparison Engine</span>
        </div>
        <h1 className="text-[34px] sm:text-[40px] font-bold text-[#0A0A0A] tracking-tight leading-tight">
          Engineering Drawing Comparison
        </h1>
        <p className="text-[15px] text-[#525252] mt-3 leading-relaxed max-w-2xl mx-auto">
          Upload baseline (Rev A) and incoming (Rev B) drawings to detect geometry deltas,
          dimension modifications, tolerance changes, and annotation notes.
        </p>
      </div>



      {/* Validation alert banner */}
      {validationError && (
        <div className="mb-6 p-4 bg-rose-50 border border-rose-200 rounded-[10px] flex items-center gap-3 text-[14px] text-rose-900">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span className="flex-1">{validationError}</span>
          <button
            onClick={() => setValidationError(null)}
            className="text-rose-600 hover:text-rose-800 text-xs font-semibold cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Two Drop Zones: Old vs New Drawing */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Left Drop Zone: Baseline (Rev A) */}
        <div
          id="dropzone-old-drawing"
          onDragOver={(e) => {
            e.preventDefault();
            setIsDraggingOld(true);
          }}
          onDragLeave={() => setIsDraggingOld(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDraggingOld(false);
            if (e.dataTransfer.files?.[0]) {
              handleFileDrop(e.dataTransfer.files[0], true);
            }
          }}
          className={`relative border-2 border-dashed rounded-[10px] p-8 flex flex-col items-center justify-center min-h-[300px] text-center transition-all ${
            isDraggingOld
              ? 'border-[#0A0A0A] bg-[#FAFAFA]'
              : oldDrawing
              ? 'border-[#21F1A8] bg-white'
              : 'border-[#21F1A8] bg-[#FAFAFA]/60 hover:bg-[#FAFAFA]'
          }`}
        >
          <input
            ref={oldFileInputRef}
            type="file"
            accept=".pdf,.dwg,.dxf,.svg,.png,.tiff,.jpg"
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.[0]) {
                handleFileDrop(e.target.files[0], true);
              }
            }}
          />

          <div className="absolute top-3.5 left-3.5 px-3 py-1 rounded-full bg-[#21F1A8] text-[#171717] text-[13px] font-semibold">
            1. Baseline drawing (Rev A)
          </div>

          {oldDrawing ? (
            <div className="w-full flex flex-col items-center">
              <div className="w-12 h-12 rounded-[10px] bg-[#FAFAFA] border border-[#E5E5E5] flex items-center justify-center text-[#0A0A0A] mb-4">
                <FileCheck className="w-6 h-6 text-[#0A0A0A]" />
              </div>
              <div className="text-[15px] font-semibold text-[#0A0A0A] max-w-[280px] truncate">
                {oldDrawing.name}
              </div>
              <div className="text-xs text-[#525252] mt-1.5">
                {oldDrawing.revision} • <span className="font-mono">{oldDrawing.fileSize}</span>
              </div>
              <div className="text-[12px] text-[#6b7280] mt-1">
                {oldDrawing.author}
              </div>

              <div className="mt-5 flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => oldFileInputRef.current?.click()}
                  className="px-3.5 py-1.5 text-xs font-medium text-[#525252] hover:text-[#0A0A0A] bg-white hover:bg-[#FAFAFA] rounded-[9999px] border border-[#E5E5E5] transition-colors cursor-pointer"
                >
                  Change File
                </button>
                <button
                  type="button"
                  onClick={() => setOldDrawing(null)}
                  className="p-1.5 text-[#A3A3A3] hover:text-[#0A0A0A] transition-colors cursor-pointer rounded-full"
                  title="Remove file"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 rounded-[10px] bg-white border border-[#E5E5E5] flex items-center justify-center text-[#A3A3A3] mb-4">
                <UploadCloud className="w-6 h-6" />
              </div>
              <div className="text-[15px] font-semibold text-[#0A0A0A]">
                Drag & drop baseline drawing here
              </div>
              <p className="text-[13px] text-[#525252] mt-1.5 mb-5">
                or click to browse from your workstation
              </p>
              <button
                type="button"
                onClick={() => oldFileInputRef.current?.click()}
                className="px-4 py-2 text-xs font-medium bg-white hover:bg-[#FAFAFA] text-[#0A0A0A] rounded-[9999px] border border-[#E5E5E5] transition-colors cursor-pointer"
              >
                Browse Baseline Drawing
              </button>
            </div>
          )}

          <div className="absolute bottom-2.5 text-[11px] text-[#A3A3A3]">
            PDF, DWG, DXF, SVG, TIFF (Max 50MB)
          </div>
        </div>

        {/* Right Drop Zone: Incoming (Rev B) */}
        <div
          id="dropzone-new-drawing"
          onDragOver={(e) => {
            e.preventDefault();
            setIsDraggingNew(true);
          }}
          onDragLeave={() => setIsDraggingNew(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDraggingNew(false);
            if (e.dataTransfer.files?.[0]) {
              handleFileDrop(e.dataTransfer.files[0], false);
            }
          }}
          className={`relative border-2 border-dashed rounded-[10px] p-8 flex flex-col items-center justify-center min-h-[300px] text-center transition-all ${
            isDraggingNew
              ? 'border-[#0A0A0A] bg-[#FAFAFA]'
              : newDrawing
              ? 'border-[#21F1A8] bg-white'
              : 'border-[#21F1A8] bg-[#FAFAFA]/60 hover:bg-[#FAFAFA]'
          }`}
        >
          <input
            ref={newFileInputRef}
            type="file"
            accept=".pdf,.dwg,.dxf,.svg,.png,.tiff,.jpg"
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.[0]) {
                handleFileDrop(e.target.files[0], false);
              }
            }}
          />

          <div className="absolute top-3.5 left-3.5 px-3 py-1 rounded-full bg-[#171717] text-white text-[13px] font-semibold">
            2. Incoming drawing (Rev B)
          </div>

          {newDrawing ? (
            <div className="w-full flex flex-col items-center">
              <div className="w-12 h-12 rounded-[10px] bg-[#FAFAFA] border border-[#E5E5E5] flex items-center justify-center text-[#0A0A0A] mb-4">
                <FileCode className="w-6 h-6 text-[#0A0A0A]" />
              </div>
              <div className="text-[15px] font-semibold text-[#0A0A0A] max-w-[280px] truncate">
                {newDrawing.name}
              </div>
              <div className="text-xs text-[#525252] mt-1.5">
                {newDrawing.revision} • <span className="font-mono">{newDrawing.fileSize}</span>
              </div>
              <div className="text-[12px] text-[#6b7280] mt-1">
                {newDrawing.author}
              </div>

              <div className="mt-5 flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => newFileInputRef.current?.click()}
                  className="px-3.5 py-1.5 text-xs font-medium text-[#525252] hover:text-[#0A0A0A] bg-white hover:bg-[#FAFAFA] rounded-[9999px] border border-[#E5E5E5] transition-colors cursor-pointer"
                >
                  Change File
                </button>
                <button
                  type="button"
                  onClick={() => setNewDrawing(null)}
                  className="p-1.5 text-[#A3A3A3] hover:text-[#0A0A0A] transition-colors cursor-pointer rounded-full"
                  title="Remove file"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 rounded-[10px] bg-white border border-[#E5E5E5] flex items-center justify-center text-[#A3A3A3] mb-4">
                <UploadCloud className="w-6 h-6" />
              </div>
              <div className="text-[15px] font-semibold text-[#0A0A0A]">
                Drag & drop revised drawing here
              </div>
              <p className="text-[13px] text-[#525252] mt-1.5 mb-5">
                or click to browse from your workstation
              </p>
              <button
                type="button"
                onClick={() => newFileInputRef.current?.click()}
                className="px-4 py-2 text-xs font-medium bg-white hover:bg-[#FAFAFA] text-[#0A0A0A] rounded-[9999px] border border-[#E5E5E5] transition-colors cursor-pointer"
              >
                Browse Revised Drawing
              </button>
            </div>
          )}

          <div className="absolute bottom-2.5 text-[11px] text-[#A3A3A3]">
            PDF, DWG, DXF, SVG, TIFF (Max 50MB)
          </div>
        </div>
      </div>

      {/* Main Action Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between border-t border-[#E5E5E5] pt-6 gap-4">
        <div className="text-xs text-[#525252] font-medium text-center sm:text-left">
          {isComparing
            ? 'Processing comparison via AI engine...'
            : isReadyToCompare
            ? 'Both drawing revisions verified and ready for VLM comparison.'
            : 'Select or upload both drawing revisions to proceed.'}
        </div>

        <button
          id="btn-run-comparison"
          type="button"
          disabled={!isReadyToCompare}
          onClick={handleExecuteComparison}
          className={`inline-flex items-center justify-center gap-2.5 px-8 py-3.5 rounded-[9999px] text-[14px] font-semibold tracking-tight transition-all ${
            isReadyToCompare
              ? 'bg-cyprus hover:bg-cyprus-deep text-white cursor-pointer shadow-md hover:shadow-lg active:scale-[0.98]'
              : 'bg-[#E5E5E5] text-[#525252] cursor-not-allowed'
          }`}
        >
          <span>Compare Drawings</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* Quick tips — fills the space below the upload card with useful guidance */}
      <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white border border-[#E5E5E5] rounded-[10px] p-4">
          <p className="text-xs font-bold text-[#0A0A0A] uppercase tracking-wider">Supported files</p>
          <p className="mt-1 text-[13px] text-[#525252] leading-relaxed">
            PDF, DWG, DXF, SVG, PNG or TIFF up to 50MB per file.
          </p>
        </div>
        <div className="bg-white border border-[#E5E5E5] rounded-[10px] p-4">
          <p className="text-xs font-bold text-[#0A0A0A] uppercase tracking-wider">Hybrid VLM Engine</p>
          <p className="mt-1 text-[13px] text-[#525252] leading-relaxed">
            Track A inventory extraction & Track B visual diff — automated end-to-end.
          </p>
        </div>
        <div className="bg-white border border-[#E5E5E5] rounded-[10px] p-4">
          <p className="text-xs font-bold text-[#0A0A0A] uppercase tracking-wider">Tracked results</p>
          <p className="mt-1 text-[13px] text-[#525252] leading-relaxed">
            Comparisons run as background jobs and stay saved in your Drawing Library.
          </p>
        </div>
      </div>
    </div>
  );
};
