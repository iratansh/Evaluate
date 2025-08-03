'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

const DOMAINS = [
  { value: 'software_engineering', label: 'Software Engineering' },
  { value: 'data_science', label: 'Data Science' },
  { value: 'ai_ml', label: 'AI/ML' },
  { value: 'hardware_ece', label: 'Hardware/ECE' },
  { value: 'robotics', label: 'Robotics' }
];

const DIFFICULTIES = [
  { value: 'easy', label: 'Easy', description: 'Entry level questions' },
  { value: 'medium', label: 'Medium', description: 'Mid-level questions' },
  { value: 'hard', label: 'Hard', description: 'Senior level questions' }
];

export default function InterviewSetup() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    domain: '',
    difficulty: 'medium',
    duration_minutes: 45
  });
  const [loading, setLoading] = useState(false);
  const [domainTopics, setDomainTopics] = useState<string[]>([]);
  const [loadingTopics, setLoadingTopics] = useState(false);

  const fetchDomainTopics = async (domain: string) => {
    if (!domain) {
      setDomainTopics([]);
      return;
    }

    setLoadingTopics(true);
    try {
      const response = await fetch(`http://localhost:8000/api/interview/domains/${domain}/topics`);
      if (response.ok) {
        const data = await response.json();
        // Extract section headers from topics
        const sections = data.topics
          .map((topic: string) => {
            const match = topic.match(/Section: ([^\n]+)/);
            return match ? match[1] : null;
          })
          .filter((section: string | null) => section && section.trim() !== '')
          .slice(0, 6); // Show first 6 sections
        setDomainTopics(sections);
      }
    } catch (error) {
      console.error('Error fetching domain topics:', error);
    } finally {
      setLoadingTopics(false);
    }
  };

  useEffect(() => {
    fetchDomainTopics(formData.domain);
  }, [formData.domain]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/interview/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        const session = await response.json();
        router.push(`/interview/session/${session.id}`);
      } else {
        throw new Error('Failed to create session');
      }
    } catch (error) {
      console.error('Error creating interview session:', error);
      alert('Failed to start interview. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-2xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-4">
              Setup Your Interview
            </h1>
            <p className="text-gray-600">
              Choose your domain and difficulty level to get started
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-lg p-8">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Domain Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Interview Domain
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {DOMAINS.map((domain) => (
                    <label
                      key={domain.value}
                      className={`
                        relative flex items-center p-4 border rounded-lg cursor-pointer
                        ${formData.domain === domain.value 
                          ? 'border-blue-500 bg-blue-50' 
                          : 'border-gray-300 hover:bg-gray-50'
                        }
                      `}
                    >
                      <input
                        type="radio"
                        name="domain"
                        value={domain.value}
                        checked={formData.domain === domain.value}
                        onChange={(e) => setFormData({...formData, domain: e.target.value})}
                        className="sr-only"
                      />
                      <span className="text-sm font-medium">{domain.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Topics Preview */}
              {formData.domain && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Topics Covered
                  </label>
                  <div className="bg-gray-50 rounded-lg p-4">
                    {loadingTopics ? (
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                        <span className="text-sm text-gray-600">Loading topics...</span>
                      </div>
                    ) : domainTopics.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {domainTopics.map((topic, index) => (
                          <div key={index} className="flex items-center space-x-2">
                            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                            <span className="text-sm text-gray-700">{topic}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="text-sm text-gray-500">Select a domain to see topics</span>
                    )}
                  </div>
                </div>
              )}

              {/* Difficulty Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Difficulty Level
                </label>
                <div className="space-y-3">
                  {DIFFICULTIES.map((diff) => (
                    <label
                      key={diff.value}
                      className={`
                        relative flex items-center p-4 border rounded-lg cursor-pointer
                        ${formData.difficulty === diff.value 
                          ? 'border-blue-500 bg-blue-50' 
                          : 'border-gray-300 hover:bg-gray-50'
                        }
                      `}
                    >
                      <input
                        type="radio"
                        name="difficulty"
                        value={diff.value}
                        checked={formData.difficulty === diff.value}
                        onChange={(e) => setFormData({...formData, difficulty: e.target.value})}
                        className="sr-only"
                      />
                      <div>
                        <div className="text-sm font-medium">{diff.label}</div>
                        <div className="text-xs text-gray-500">{diff.description}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Duration */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Interview Duration (minutes)
                </label>
                <select
                  value={formData.duration_minutes}
                  onChange={(e) => setFormData({...formData, duration_minutes: parseInt(e.target.value)})}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value={30}>30 minutes</option>
                  <option value={45}>45 minutes</option>
                  <option value={60}>60 minutes</option>
                </select>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={!formData.domain || loading}
                className={`
                  w-full py-3 px-6 rounded-lg font-semibold transition duration-200
                  ${formData.domain && !loading
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  }
                `}
              >
                {loading ? 'Starting Interview...' : 'Start Interview'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
