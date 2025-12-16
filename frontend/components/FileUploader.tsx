"use client";

import { useState } from "react";
import { Upload, Loader2, Music } from "lucide-react";
import { useAuth } from "../context/AuthContext";

interface FileUploaderProps {
  onDataReceived: (data: any) => void;
}

export default function FileUploader({ onDataReceived }: FileUploaderProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { token } = useAuth();

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;

    if (!token) {
        setError("You must be logged in to upload files.");
        return;
    }

    setUploading(true);
    setError(null);

    const formData = new FormData();
    // Append all selected files to the form data
    Array.from(e.target.files).forEach((file) => {
      formData.append("files", file);
    });

    try {
      // Note: We use localhost:8000 here because the BROWSER (client) 
      // is talking to the API, not the Docker container.
      const response = await fetch("http://localhost:8000/api/process", {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${token}`
        },
        body: formData,
      });

      if (!response.ok) {
          const errData = await response.json().catch(() => ({ detail: "Upload failed" }));
          throw new Error(errData.detail || "Upload failed");
      }

      const data = await response.json();
      onDataReceived(data); // Pass data back up to the parent
    } catch (err: any) {
      setError(err.message || "Failed to process files. Make sure the backend is running!");
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center p-12 border-2 border-dashed border-slate-700 rounded-xl bg-slate-900/50 hover:border-slate-500 transition-all group">
      <div className="mb-4 p-4 bg-slate-800 rounded-full group-hover:bg-slate-700 transition-colors">
        {uploading ? (
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
        ) : (
          <Upload className="w-8 h-8 text-blue-400" />
        )}
      </div>
      
      <h3 className="text-xl font-bold mb-2">Drop your Spotify History</h3>
      <p className="text-slate-400 text-sm mb-6 text-center max-w-sm">
        Upload the JSON files from your "Extended Streaming History" folder.
      </p>

      <label className="cursor-pointer bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 px-6 rounded-lg transition-transform hover:scale-105 active:scale-95 shadow-[0_0_15px_rgba(37,99,235,0.5)]">
        Select Files
        <input
          type="file"
          multiple
          accept=".json"
          className="hidden"
          onChange={handleFileUpload}
          disabled={uploading}
        />
      </label>

      {error && <p className="mt-4 text-red-400 text-sm">{error}</p>}
    </div>
  );
}