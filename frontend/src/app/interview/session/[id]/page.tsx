'use client';

import { useState, useEffect, useRef, use } from 'react';
import { useRouter } from 'next/navigation';

interface Question {
  id: number;
  session_id: number;
  question_text: string;
  question_type: string;
}

interface Session {
  id: number;
  domain: string;
  difficulty: string;
  status: string;
  duration_minutes: number;
}

export default function InterviewSession({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const resolvedParams = use(params);
  const [session, setSession] = useState<Session | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [answer, setAnswer] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [feedback, setFeedback] = useState<{score: number, feedback: string, suggestions?: string[]} | null>(null);
  const [loading, setLoading] = useState(false);
  const [questionCount, setQuestionCount] = useState(0);
  const [elapsedTime, setElapsedTime] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    const initializeSession = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/interview/sessions/${resolvedParams.id}`);
        if (response.ok) {
          const sessionData = await response.json();
          setSession(sessionData);
          
          // Get first question
          const questionResponse = await fetch('http://localhost:8000/api/interview/questions', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              session_id: parseInt(resolvedParams.id),
              context: null
            }),
          });

          if (questionResponse.ok) {
            const question = await questionResponse.json();
            setCurrentQuestion(question);
            setQuestionCount(1);
          } else {
            console.error('Failed to get first question');
          }
        } else {
          console.error('Failed to fetch session');
        }
      } catch (error) {
        console.error('Error initializing session:', error);
      }
    };

    initializeSession();
    
    const startTimeNow = new Date();
    
    // Timer
    const timer = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTimeNow.getTime()) / 1000));
    }, 1000);

    return () => clearInterval(timer);
  }, [resolvedParams.id]);

  const getNextQuestion = async () => {
    if (!session) {
      console.error('No session available');
      return;
    }
    
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/interview/questions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: parseInt(resolvedParams.id),
          context: currentQuestion ? `Previous question: ${currentQuestion.question_text}` : null
        }),
      });

      if (response.ok) {
        const question = await response.json();
        setCurrentQuestion(question);
        setAnswer('');
        setFeedback(null);
        setQuestionCount(prev => prev + 1);
      } else {
        console.error('Failed to get next question');
      }
    } catch (error) {
      console.error('Error getting next question:', error);
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async () => {
    if (!currentQuestion || !answer.trim()) return;

    setLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/api/interview/questions/${currentQuestion.id}/answer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question_id: currentQuestion.id,
          answer_text: answer
        }),
      });

      if (response.ok) {
        const feedbackData = await response.json();
        setFeedback(feedbackData);
      }
    } catch (error) {
      console.error('Error submitting answer:', error);
    } finally {
      setLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        await submitAudioAnswer(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error starting recording:', error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const submitAudioAnswer = async (audioBlob: Blob) => {
    if (!currentQuestion) return;

    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'answer.wav');

    setLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/api/interview/questions/${currentQuestion.id}/audio`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const feedbackData = await response.json();
        setFeedback(feedbackData);
      }
    } catch (error) {
      console.error('Error submitting audio answer:', error);
    } finally {
      setLoading(false);
    }
  };

  const completeInterview = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/interview/sessions/${resolvedParams.id}/complete`, {
        method: 'PUT',
      });

      if (response.ok) {
        router.push(`/interview/results/${resolvedParams.id}`);
      }
    } catch (error) {
      console.error('Error completing interview:', error);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!session || !currentQuestion) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p>Loading interview...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-xl font-semibold">{session.domain} Interview</h1>
              <p className="text-sm text-gray-600">Question {questionCount}</p>
            </div>
            <div className="text-right">
              <div className="text-lg font-mono">{formatTime(elapsedTime)}</div>
              <div className="text-sm text-gray-600">
                {session.duration_minutes} min session
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Question */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <div className="flex items-center mb-4">
              <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                {currentQuestion.question_type}
              </span>
            </div>
            <h2 className="text-xl font-semibold mb-4">
              {currentQuestion.question_text}
            </h2>
          </div>

          {/* Answer Input */}
          {!feedback && (
            <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Your Answer
                  </label>
                  <textarea
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    placeholder="Type your answer here..."
                    rows={6}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div className="flex space-x-4">
                  <button
                    onClick={submitAnswer}
                    disabled={!answer.trim() || loading}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300"
                  >
                    {loading ? 'Submitting...' : 'Submit Answer'}
                  </button>

                  <button
                    onClick={isRecording ? stopRecording : startRecording}
                    className={`px-6 py-2 rounded-lg ${
                      isRecording 
                        ? 'bg-red-600 text-white hover:bg-red-700' 
                        : 'bg-gray-600 text-white hover:bg-gray-700'
                    }`}
                  >
                    {isRecording ? '⏹ Stop Recording' : '🎤 Record Answer'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Feedback */}
          {feedback && (
            <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
              <h3 className="text-lg font-semibold mb-4">Feedback</h3>
              
              <div className="mb-4">
                <div className="flex items-center mb-2">
                  <span className="text-sm font-medium text-gray-700">Score:</span>
                  <span className="ml-2 text-lg font-bold text-blue-600">
                    {feedback.score}/10
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full"
                    style={{ width: `${(feedback.score / 10) * 100}%` }}
                  ></div>
                </div>
              </div>

              <div className="mb-4">
                <h4 className="font-medium text-gray-700 mb-2">Feedback:</h4>
                <p className="text-gray-600">{feedback.feedback}</p>
              </div>

              {feedback.suggestions && feedback.suggestions.length > 0 && (
                <div className="mb-6">
                  <h4 className="font-medium text-gray-700 mb-2">Suggestions:</h4>
                  <ul className="list-disc list-inside text-gray-600 space-y-1">
                    {feedback.suggestions.map((suggestion: string, index: number) => (
                      <li key={index}>{suggestion}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex space-x-4">
                <button
                  onClick={getNextQuestion}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Next Question
                </button>
                
                <button
                  onClick={completeInterview}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Complete Interview
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
