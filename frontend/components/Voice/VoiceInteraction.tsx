'use client';

import { useState, useRef } from 'react';
import Card from '../UI/Card';
import Button from '../UI/Button';

interface VoiceResult {
  text: string;
  confidence: number;
  language: string;
  intent: string;
  entities: Record<string, any>;
  action: string;
  parameters: Record<string, any>;
}

export default function VoiceInteraction() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<VoiceResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState('en-US');
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const languages = [
    { code: 'en-US', name: 'English (US)' },
    { code: 'en-GB', name: 'English (UK)' },
    { code: 'es-ES', name: 'Spanish' },
    { code: 'fr-FR', name: 'French' },
    { code: 'de-DE', name: 'German' },
    { code: 'it-IT', name: 'Italian' },
    { code: 'pt-BR', name: 'Portuguese (Brazil)' },
    { code: 'ja-JP', name: 'Japanese' },
    { code: 'ko-KR', name: 'Korean' },
    { code: 'zh-CN', name: 'Chinese (Simplified)' }
  ];

  const startRecording = async () => {
    try {
      setError(null);
      setResult(null);

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        await processAudio(audioBlob);

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);

      // Auto-stop after 10 seconds
      setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          stopRecording();
        }
      }, 10000);

    } catch (error) {
      console.error('Error starting recording:', error);
      setError('Could not access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const processAudio = async (audioBlob: Blob) => {
    setIsProcessing(true);

    try {
      // Convert blob to base64
      const base64Audio = await blobToBase64(audioBlob);

      // Send to voice processing API
      const response = await fetch('/api/voice/process/base64', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          audio_data: base64Audio,
          language: selectedLanguage
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setResult(data);
      } else {
        setError(data.detail || 'Voice processing failed');
      }

    } catch (error) {
      console.error('Error processing audio:', error);
      setError('Failed to process audio. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const blobToBase64 = (blob: Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = (reader.result as string).split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setError(null);
    setResult(null);
    setIsProcessing(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`/api/voice/process/audio?language=${selectedLanguage}`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        setResult(data);
      } else {
        setError(data.detail || 'Voice processing failed');
      }

    } catch (error) {
      console.error('Error processing uploaded file:', error);
      setError('Failed to process audio file. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const getIntentColor = (intent: string) => {
    const colors: Record<string, string> = {
      search: 'bg-blue-100 text-blue-800',
      analyze: 'bg-green-100 text-green-800',
      create: 'bg-purple-100 text-purple-800',
      schedule: 'bg-orange-100 text-orange-800',
      report: 'bg-indigo-100 text-indigo-800',
      default: 'bg-gray-100 text-gray-800'
    };

    return colors[intent] || colors.default;
  };

  return (
    <div className="space-y-6">
      {/* Voice Controls */}
      <Card title="Voice Recording">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Language
            </label>
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {languages.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col sm:flex-row gap-4">
            <Button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isProcessing}
              className={`flex-1 ${isRecording ? 'bg-red-600 hover:bg-red-700' : ''}`}
            >
              {isRecording ? '🔴 Stop Recording' : '🎤 Start Recording'}
            </Button>

            <div className="flex-1">
              <label className="block w-full">
                <Button variant="outline" className="w-full" disabled={isProcessing}>
                  📁 Upload Audio File
                </Button>
                <input
                  type="file"
                  accept="audio/*"
                  onChange={handleFileUpload}
                  className="hidden"
                  disabled={isProcessing}
                />
              </label>
            </div>
          </div>

          {isRecording && (
            <div className="text-center text-red-600 font-medium">
              🎤 Recording... (Will auto-stop in 10 seconds)
            </div>
          )}

          {isProcessing && (
            <div className="text-center text-blue-600 font-medium">
              🔄 Processing audio...
            </div>
          )}

          {error && (
            <div className="text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
              {error}
            </div>
          )}
        </div>
      </Card>

      {/* Results */}
      {result && (
        <Card title="Voice Processing Results">
          <div className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Recognized Text</h3>
                <p className="text-gray-700 bg-gray-50 p-3 rounded-md">
                  "{result.text}"
                </p>
                <div className="mt-2 text-sm text-gray-600">
                  Confidence: {(result.confidence * 100).toFixed(1)}% |
                  Language: {result.language}
                </div>
              </div>

              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Intent Analysis</h3>
                <div className="space-y-2">
                  <div>
                    <span className="text-sm text-gray-600">Intent: </span>
                    <span className={`px-2 py-1 text-xs rounded capitalize ${getIntentColor(result.intent)}`}>
                      {result.intent.replace('_', ' ')}
                    </span>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Action: </span>
                    <span className="text-sm text-gray-900">{result.action}</span>
                  </div>
                </div>
              </div>
            </div>

            {Object.keys(result.entities).length > 0 && (
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Extracted Entities</h3>
                <div className="bg-gray-50 p-3 rounded-md">
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                    {JSON.stringify(result.entities, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {Object.keys(result.parameters).length > 0 && (
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Action Parameters</h3>
                <div className="bg-gray-50 p-3 rounded-md">
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                    {JSON.stringify(result.parameters, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Instructions */}
      <Card title="Voice Commands">
        <div className="space-y-4">
          <p className="text-gray-600">
            Try speaking these example commands to test the voice recognition:
          </p>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <h4 className="font-medium text-gray-900">Search Commands</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• "Search for AI news"</li>
                <li>• "Find information about stocks"</li>
                <li>• "Look up weather forecast"</li>
              </ul>
            </div>

            <div className="space-y-2">
              <h4 className="font-medium text-gray-900">Analysis Commands</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• "Analyze market trends"</li>
                <li>• "Check financial reports"</li>
                <li>• "Summarize this article"</li>
              </ul>
            </div>

            <div className="space-y-2">
              <h4 className="font-medium text-gray-900">Task Commands</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• "Create a daily report"</li>
                <li>• "Schedule a meeting"</li>
                <li>• "Generate summary"</li>
              </ul>
            </div>

            <div className="space-y-2">
              <h4 className="font-medium text-gray-900">Tips</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Speak clearly and slowly</li>
                <li>• Minimize background noise</li>
                <li>• Use natural language</li>
                <li>• Keep recordings under 10 seconds</li>
              </ul>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
