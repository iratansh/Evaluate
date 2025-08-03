"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

interface Question {
  id: number;
  session_id: number;
  question_text: string;
  user_answer: string | null;
  score: number | null;
  feedback: string | null;
}

interface Session {
  id: number;
  domain: string;
  difficulty: string;
  status: string;
  duration_minutes: number;
  score: number | null;
  created_at: string;
  completed_at: string | null;
}

export default function InterviewResults() {
  const params = useParams();
  const sessionId = params?.id as string;

  const [session, setSession] = useState<Session | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setError("No session ID provided");
      return;
    }

    const fetchResults = async () => {
      try {
        // Fetch session details
        const sessionResponse = await fetch(
          `http://localhost:8000/api/interview/sessions/${sessionId}`
        );
        if (!sessionResponse.ok) {
          throw new Error("Failed to fetch session details");
        }
        const sessionData = await sessionResponse.json();
        setSession(sessionData);

        // Fetch session questions
        const questionsResponse = await fetch(
          `http://localhost:8000/api/interview/sessions/${sessionId}/questions`
        );
        if (!questionsResponse.ok) {
          throw new Error("Failed to fetch questions");
        }
        const questionsData = await questionsResponse.json();
        setQuestions(questionsData);

      } catch (error) {
        console.error("Error fetching results:", error);
        setError("Failed to load interview results");
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [sessionId]);

  const formatDuration = (startTime: string, endTime: string | null) => {
    if (!endTime) return "N/A";
    const start = new Date(startTime);
    const end = new Date(endTime);
    const diffMinutes = Math.floor((end.getTime() - start.getTime()) / (1000 * 60));
    return `${diffMinutes} minutes`;
  };

  const getScoreColor = (score: number | null) => {
    if (!score) return "text-gray-500";
    if (score >= 8) return "text-green-600";
    if (score >= 6) return "text-yellow-600";
    return "text-red-600";
  };

  const getScoreLabel = (score: number | null) => {
    if (!score) return "Not scored";
    if (score >= 8) return "Excellent";
    if (score >= 6) return "Good";
    if (score >= 4) return "Fair";
    return "Needs Improvement";
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your results...</p>
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center p-8 bg-white rounded-lg shadow-lg max-w-md">
          <div className="text-red-600 mb-4">
            <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Unable to Load Results
          </h2>
          <p className="text-gray-600 mb-6">
            {error || "The interview results could not be found."}
          </p>
          <Link 
            href="/interview/setup"
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition duration-200"
          >
            Start New Interview
          </Link>
        </div>
      </div>
    );
  }

  const answeredQuestions = questions.filter(q => q.user_answer);
  const averageScore = answeredQuestions.length > 0 
    ? answeredQuestions.reduce((sum, q) => sum + (q.score || 0), 0) / answeredQuestions.length
    : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <div className="text-center">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Interview Results
              </h1>
              <p className="text-gray-600">
                {session.domain} • {session.difficulty.charAt(0).toUpperCase() + session.difficulty.slice(1)} Level
              </p>
            </div>
          </div>

          {/* Summary */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Summary</h2>
            <div className="grid md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className={`text-3xl font-bold ${getScoreColor(averageScore)}`}>
                  {averageScore ? averageScore.toFixed(1) : "N/A"}
                </div>
                <div className="text-sm text-gray-600">Overall Score</div>
                <div className={`text-sm font-medium ${getScoreColor(averageScore)}`}>
                  {getScoreLabel(averageScore)}
                </div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-blue-600">
                  {answeredQuestions.length}
                </div>
                <div className="text-sm text-gray-600">Questions Answered</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-green-600">
                  {formatDuration(session.created_at, session.completed_at)}
                </div>
                <div className="text-sm text-gray-600">Duration</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-purple-600">
                  {session.status.charAt(0).toUpperCase() + session.status.slice(1)}
                </div>
                <div className="text-sm text-gray-600">Status</div>
              </div>
            </div>
          </div>

          {/* Detailed Results */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Question Details</h2>
            <div className="space-y-6">
              {questions.map((question, index) => (
                <div key={question.id} className="border-l-4 border-blue-200 pl-4">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-medium text-gray-900">
                      Question {index + 1}
                    </h3>
                    {question.score && (
                      <span className={`px-2 py-1 rounded-full text-sm font-medium ${
                        question.score >= 8 ? 'bg-green-100 text-green-800' :
                        question.score >= 6 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {question.score.toFixed(1)}/10
                      </span>
                    )}
                  </div>
                  <p className="text-gray-700 mb-3">{question.question_text}</p>
                  
                  {question.user_answer ? (
                    <>
                      <div className="bg-gray-50 rounded-lg p-3 mb-3">
                        <h4 className="font-medium text-gray-700 mb-1">Your Answer:</h4>
                        <p className="text-gray-600">{question.user_answer}</p>
                      </div>
                      
                      {question.feedback && (
                        <div className="bg-blue-50 rounded-lg p-3">
                          <h4 className="font-medium text-blue-700 mb-1">Feedback:</h4>
                          <p className="text-blue-600">{question.feedback}</p>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-gray-500 italic">No answer provided</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/interview/setup"
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition duration-200 text-center"
              >
                Start New Interview
              </Link>
              <Link
                href="/"
                className="px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition duration-200 text-center"
              >
                Back to Home
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
