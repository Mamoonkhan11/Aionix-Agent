'use client';

import VoiceInteraction from '../../../components/Voice/VoiceInteraction';

export default function VoicePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Voice Interaction</h1>
        <p className="text-gray-600 mt-2">
          Communicate with AI agents using voice commands. Speak naturally and get intelligent responses.
        </p>
      </div>

      <VoiceInteraction />
    </div>
  );
}
