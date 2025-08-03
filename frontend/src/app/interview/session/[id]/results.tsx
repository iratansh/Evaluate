// app/interview/results/[id]/page.tsx

'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';

interface SessionResult {
  id: number;
  domain: string;
  difficulty: string;
  status: string;
  score: number | null;
  duration_minutes: number;
  created_at: string;
  completed_at: string | null;
}

interface QuestionResult {
  id: number;
  question_text: string;
  user_answer: string | null;
  score: number | null;
  feedback: string | null;
}

export default function InterviewResults() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params?.id as string;
  
  const [session, setSession] = useState<SessionResult | null>(null);
  const [questions, setQuestions] = useState<QuestionResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setError('No session ID provided');
      return;
    }

    const fetchResults = async () => {
      try {
        // Fetch session details
        const sessionResponse = await fetch(`http://localhost:8000/api/interview/sessions/${sessionId}`);
        if (!sessionResponse.ok) {
          throw new Error('Failed to fetch session results');
        }
        
        const sessionData = await sessionResponse.json();
        setSession(sessionData);
        
        // Fetch questions for this session
        const questionsResponse = await fetch(`http://localhost:8000/api/interview/sessions/${sessionId}/questions`);
        if (questionsResponse.ok) {
          const questionsData = await questionsResponse.json();
          setQuestions(questionsData);
        }
        
      } catch (error) {
        console.error('Error fetching results:', error);
        setError(error instanceof Error ? error.message : 'Failed to load results');
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [sessionId]);

  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600';
    if (score >= 6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreMessage = (score: number) => {
    if (score >= 8) return 'Excellent Performance!';
    if (score >= 6) return 'Good Performance';
    if (score >= 4) return 'Needs Improvement';
    return 'Keep Practicing';
  };

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center p-8 bg-white rounded-lg shadow-lg">
          <div className="text-red-600 mb-4">
            <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Error</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <Link
            href="/"
            className="inline-block px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading results...</p>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="text-gray-600">No results found</p>
        </div>
      </div>
    );
  }

  const finalScore = session.score || 0;
  const answeredQuestions = questions.filter(q => q.score !== null);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              Interview Results
            </h1>
            <p className="text-xl text-gray-600">
              {session.domain} - {session.difficulty} Level
            </p>
          </div>

          {/* Overall Score Card */}
          <div className="bg-white rounded-lg shadow-lg p-8 mb-8 text-center">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Overall Score</h2>
            <div className={`text-6xl font-bold mb-4 ${getScoreColor(finalScore)}`}>
              {finalScore.toFixed(1)}/10
            </div>
            <p className={`text-xl font-medium ${getScoreColor(finalScore)}`}>
              {getScoreMessage(finalScore)}
            </p>
            
            {/* Score Bar */}
            <div className="mt-6 max-w-md mx-auto">
              <div className="w-full bg-gray-200 rounded-full h-4">
                <div 
                  className={`h-4 rounded-full ${
                    finalScore >= 8 ? 'bg-green-600' : 
                    finalScore >= 6 ? 'bg-yellow-600' : 'bg-red-600'
                  }`}
                  style={{ width: `${(finalScore / 10) * 100}%` }}
                ></div>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4 mt-8">
              <div>
                <p className="text-gray-600">Duration</p>
                <p className="text-xl font-semibold text-gray-900">
                  {session.duration_minutes} min
                </p>
              </div>
              <div>
                <p className="text-gray-600">Questions</p>
                <p className="text-xl font-semibold text-gray-900">
                  {answeredQuestions.length}
                </p>
              </div>
              <div>
                <p className="text-gray-600">Difficulty</p>
                <p className="text-xl font-semibold capitalize text-gray-900">
                  {session.difficulty}
                </p>
              </div>
            </div>
          </div>

          {/* Question-by-Question Review */}
          {answeredQuestions.length > 0 && (
            <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-6">Question Review</h2>
              <div className="space-y-6">
                {answeredQuestions.map((question, index) => (
                  <div key={question.id} className="border-b border-gray-200 pb-6 last:border-0">
                    <h3 className="font-semibold text-lg text-gray-900 mb-2">
                      Question {index + 1}: {question.question_text}
                    </h3>
                    {question.user_answer && (
                      <div className="mb-3">
                        <p className="text-sm font-medium text-gray-700 mb-1">Your Answer:</p>
                        <p className="text-gray-600 bg-gray-50 p-3 rounded">{question.user_answer}</p>
                      </div>
                    )}
                    <div className="flex items-center mb-2">
                      <span className="text-sm font-medium text-gray-700">Score:</span>
                      <span className={`ml-2 font-bold ${getScoreColor(question.score || 0)}`}>
                        {question.score}/10
                      </span>
                    </div>
                    {question.feedback && (
                      <div>
                        <p className="text-sm font-medium text-gray-700 mb-1">Feedback:</p>
                        <p className="text-gray-600">{question.feedback}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Detailed Feedback */}
          <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">Key Takeaways</h2>
            
            <div className="space-y-4">
              <div className="border-l-4 border-blue-500 pl-4">
                <h3 className="font-semibold text-lg text-gray-900 mb-2">Strengths</h3>
                <ul className="list-disc list-inside text-gray-600 space-y-1">
                  <li>Clear communication and structure in answers</li>
                  <li>Good understanding of fundamental concepts</li>
                  <li>Practical examples provided when relevant</li>
                </ul>
              </div>

              <div className="border-l-4 border-yellow-500 pl-4">
                <h3 className="font-semibold text-lg text-gray-900 mb-2">Areas for Improvement</h3>
                <ul className="list-disc list-inside text-gray-600 space-y-1">
                  <li>Dive deeper into technical implementation details</li>
                  <li>Consider edge cases in problem-solving questions</li>
                  <li>Practice time management for complex questions</li>
                </ul>
              </div>

              <div className="border-l-4 border-green-500 pl-4">
                <h3 className="font-semibold text-lg text-gray-900 mb-2">Next Steps</h3>
                <ul className="list-disc list-inside text-gray-600 space-y-1">
                  <li>Review advanced {session.domain.toLowerCase()} concepts</li>
                  <li>Practice more {session.difficulty} level questions</li>
                  <li>Focus on system design and architecture patterns</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex justify-center space-x-4">
            <Link
              href="/interview/setup"
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold"
            >
              Start New Interview
            </Link>
            <Link
              href="/"
              className="px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 font-semibold"
            >
              Back to Home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}