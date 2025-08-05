'use client';

import React from 'react';
import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            AI Interview Practice
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Practice technical interviews with AI-powered questions tailored to your target job. 
            Get real-time feedback and improve your interview skills.
          </p>
        </div>

        <div className="max-w-md mx-auto">
          <Link 
            href="/interview/setup"
            className="block w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg text-center transition duration-200"
          >
            Start Interview Practice
          </Link>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mt-16">
          {/* Feature cards */}
          <FeatureCard 
            title="AI-Powered Questions"
            description="Questions generated based on your target job requirements"
            icon="🤖"
          />
          <FeatureCard 
            title="Voice Interaction"
            description="Practice speaking answers with speech recognition"
            icon="🎤"
          />
          <FeatureCard 
            title="Real-time Feedback"
            description="Get instant feedback and suggestions for improvement"
            icon="💬"
          />
          <FeatureCard 
            title="Multiple Domains"
            description="Software, Data Science, AI/ML, Hardware, Robotics"
            icon="🔧"
          />
          <FeatureCard 
            title="Adaptive Difficulty"
            description="Questions adjust based on your responses"
            icon="📈"
          />
          <FeatureCard 
            title="Progress Tracking"
            description="Track your improvement over time"
            icon="📊"
          />
        </div>
      </div>
    </div>
  );
}

function FeatureCard({ title, description, icon }: {
  title: string;
  description: string;
  icon: string;
}) {
  return (
    <div className="bg-white rounded-lg p-6 shadow-sm">
      <div className="text-2xl mb-3">{icon}</div>
      <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-600 text-sm">{description}</p>
    </div>
  );
}