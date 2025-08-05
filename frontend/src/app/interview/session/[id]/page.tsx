"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import ProfessionalAvatar from "./avatar";

// Extend Window interface for webkit audio context
declare global {
  interface Window {
    webkitAudioContext: typeof AudioContext;
  }
}

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
  created_at: string;
}

export default function InterviewSession() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params?.id as string;

  const [session, setSession] = useState<Session | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [answer, setAnswer] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [feedback, setFeedback] = useState<{
    score: number;
    feedback: string;
    suggestions?: string[];
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [questionCount, setQuestionCount] = useState(0);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [showTimeWarning, setShowTimeWarning] = useState(false);

  // Audio related states
  const [isPlayingTTS, setIsPlayingTTS] = useState(false);
  const [isPlayingFeedbackTTS, setIsPlayingFeedbackTTS] = useState(false);
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null);
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  // const startTimeRef = useRef<Date | null>(null);
  const sessionStartTimeRef = useRef<Date | null>(null);
  const initializationRef = useRef<boolean>(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const autoRedirectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setError("No session ID provided");
      return;
    }

    // Prevent duplicate initialization with a more robust check
    if (initializationRef.current) {
      console.log("Skipping duplicate initialization");
      return;
    }

    console.log("Starting session initialization for session:", sessionId);
    initializationRef.current = true;

    const initializeSession = async () => {
      try {
        // Fetch session details
        console.log("Fetching session details...");
        const response = await fetch(
          `http://localhost:8000/api/interview/sessions/${sessionId}`
        );
        if (!response.ok) {
          throw new Error("Failed to fetch session");
        }

        const sessionData = await response.json();
        console.log("Session data received:", sessionData);
        setSession(sessionData);

        // Parse session start time properly (handle potential timezone issues)
        const sessionStartTime = new Date(
          sessionData.created_at +
            (sessionData.created_at.includes("Z") ? "" : "Z")
        );
        sessionStartTimeRef.current = sessionStartTime;

        console.log("Session start time:", sessionStartTime);
        console.log("Current time:", new Date());

        const sessionDurationMs = sessionData.duration_minutes * 60 * 1000;
        const currentTime = new Date();
        const elapsedMs = currentTime.getTime() - sessionStartTime.getTime();
        const remainingMs = sessionDurationMs - elapsedMs;

        console.log("Session duration (ms):", sessionDurationMs);
        console.log("Elapsed (ms):", elapsedMs);
        console.log("Remaining (ms):", remainingMs);

        // Check if session has already expired
        if (remainingMs <= 0) {
          console.log("Session has expired, redirecting...");
          await completeSessionAndRedirect(sessionId);
          return;
        }

        // Set initial time states
        setElapsedTime(Math.max(0, Math.floor(elapsedMs / 1000)));
        setTimeRemaining(Math.max(0, Math.floor(remainingMs / 1000)));

        // Get first question - add a small delay to prevent race conditions
        console.log("Fetching first question...");
        await new Promise((resolve) => setTimeout(resolve, 100)); // 100ms delay

        const questionResponse = await fetch(
          "http://localhost:8000/api/interview/questions",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              session_id: parseInt(sessionId),
              context: null,
            }),
          }
        );

        if (!questionResponse.ok) {
          throw new Error("Failed to get first question");
        }

        const question = await questionResponse.json();
        console.log("First question received:", question);
        setCurrentQuestion(question);
        setQuestionCount(1);

        // Initialize audio context
        const AudioContextClass =
          window.AudioContext || window.webkitAudioContext;
        const ctx = new AudioContextClass();
        const analyserNode = ctx.createAnalyser();
        analyserNode.fftSize = 256;
        setAudioContext(ctx);
        setAnalyser(analyserNode);

        // Set up auto-redirect timer
        if (remainingMs > 30000) {
          // If more than 30 seconds left
          // Show warning 30 seconds before end
          autoRedirectTimeoutRef.current = setTimeout(() => {
            setShowTimeWarning(true);
            // Auto-redirect after warning
            setTimeout(async () => {
              await completeSessionAndRedirect(sessionId);
            }, 30000);
          }, remainingMs - 30000);
        } else {
          // Less than 30 seconds left, show warning immediately and redirect soon
          setShowTimeWarning(true);
          autoRedirectTimeoutRef.current = setTimeout(async () => {
            await completeSessionAndRedirect(sessionId);
          }, remainingMs);
        }

        console.log("Session initialization completed successfully");
      } catch (error) {
        console.error("Error initializing session:", error);
        setError(
          error instanceof Error
            ? error.message
            : "Failed to initialize session"
        );
        // Reset initialization flag on error so retry is possible
        initializationRef.current = false;
      }
    };

    initializeSession();

    return () => {
      console.log("Cleaning up session initialization");
      // Cleanup timers
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      if (autoRedirectTimeoutRef.current) {
        clearTimeout(autoRedirectTimeoutRef.current);
      }
      // DON'T reset initialization flag here to prevent re-initialization
    };
  }, []); // Remove sessionId from dependency array to prevent re-runs

  // Separate timer effect that depends on sessionId
  useEffect(() => {
    if (!sessionStartTimeRef.current || !session || !sessionId) return;

    const updateTimer = () => {
      const currentTime = new Date();
      const sessionStartTime = sessionStartTimeRef.current!;
      const sessionDurationMs = session.duration_minutes * 60 * 1000;
      const elapsedMs = currentTime.getTime() - sessionStartTime.getTime();
      const remainingMs = Math.max(0, sessionDurationMs - elapsedMs);

      const elapsedSeconds = Math.max(0, Math.floor(elapsedMs / 1000));
      const remainingSeconds = Math.max(0, Math.floor(remainingMs / 1000));

      setElapsedTime(elapsedSeconds);
      setTimeRemaining(remainingSeconds);

      // If time is up, redirect
      if (remainingMs <= 0) {
        console.log("Timer expired, redirecting to results...");
        completeSessionAndRedirect(sessionId);
      }
    };

    // Update immediately
    updateTimer();

    // Set up interval
    timerRef.current = setInterval(updateTimer, 1000);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [session, sessionId]); // Keep sessionId dependency here for timer

  const completeSessionAndRedirect = async (sessionId: string) => {
    try {
      await fetch(
        `http://localhost:8000/api/interview/sessions/${sessionId}/complete`,
        {
          method: "PUT",
        }
      );
    } catch (error) {
      console.error("Error completing session:", error);
    } finally {
      // Redirect regardless of completion success/failure
      router.push(`/interview/results/${sessionId}`);
    }
  };

  const playQuestionAudio = async () => {
    if (!currentQuestion || !audioContext || !analyser) return;

    try {
      setIsPlayingTTS(true);

      // Fetch audio from backend
      const response = await fetch(
        `http://localhost:8000/api/interview/questions/${currentQuestion.id}/speech`
      );

      if (!response.ok) {
        // Check if it's a JSON response indicating TTS is not available
        try {
          const errorData = await response.json();
          if (errorData.error) {
            console.log("TTS not available:", errorData.error);
            setIsPlayingTTS(false);
            return;
          }
        } catch {
          // Not JSON, continue with original error handling
        }
        throw new Error("Failed to get audio");
      }

      const contentType = response.headers.get("content-type");

      // Check if response is JSON (error case)
      if (contentType?.includes("application/json")) {
        const errorData = await response.json();
        console.log("TTS not available:", errorData.error);
        setIsPlayingTTS(false);
        return;
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);

      // Create and play audio
      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      // Connect to analyser
      const source = audioContext.createMediaElementSource(audio);
      source.connect(analyser);
      analyser.connect(audioContext.destination);

      audio.onended = () => {
        setIsPlayingTTS(false);
        URL.revokeObjectURL(audioUrl);
      };

      await audio.play();
    } catch (error) {
      console.error("Error playing audio:", error);
      setIsPlayingTTS(false);
    }
  };

  const playFeedbackAudio = async () => {
    if (!feedback || !audioContext || !analyser) return;

    try {
      setIsPlayingFeedbackTTS(true);

      // Create the feedback text to be spoken
      let feedbackText = `Your score is ${feedback.score} out of 10. ${feedback.feedback}`;
      
      // Add suggestions if they exist
      if (feedback.suggestions && feedback.suggestions.length > 0) {
        feedbackText += ` Here are some suggestions for improvement: ${feedback.suggestions.join('. ')}.`;
      }

      // Fetch audio from backend
      const response = await fetch(
        `http://localhost:8000/api/interview/feedback/speech`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ text: feedbackText }),
        }
      );

      if (!response.ok) {
        // Check if it's a JSON response indicating TTS is not available
        try {
          const errorData = await response.json();
          if (errorData.error) {
            console.log("TTS not available:", errorData.error);
            setIsPlayingFeedbackTTS(false);
            return;
          }
        } catch {
          // If JSON parsing fails, it's likely another error
        }
        throw new Error("Failed to get audio");
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);

      // Create and play audio
      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      // Connect to analyser
      const source = audioContext.createMediaElementSource(audio);
      source.connect(analyser);
      analyser.connect(audioContext.destination);

      audio.onended = () => {
        setIsPlayingFeedbackTTS(false);
        URL.revokeObjectURL(audioUrl);
      };

      await audio.play();
    } catch (error) {
      console.error("Error playing feedback audio:", error);
      setIsPlayingFeedbackTTS(false);
    }
  };

  const getNextQuestion = async () => {
    if (!session || !sessionId) {
      console.error("No session available");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        "http://localhost:8000/api/interview/questions",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            session_id: parseInt(sessionId),
            context: `Previous question: ${
              currentQuestion?.question_text || ""
            }. Moving to next question.`,
          }),
        }
      );

      if (!response.ok) {
        // const errorData = await response.json();
        if (response.status === 410) {
          // Time expired
          await completeSessionAndRedirect(sessionId);
          return;
        }
        throw new Error("Failed to get next question");
      }

      const question = await response.json();
      setCurrentQuestion(question);
      setAnswer("");
      setFeedback(null);
      setQuestionCount((prev) => prev + 1);
    } catch (error) {
      console.error("Error getting next question:", error);
      setError("Failed to get next question");
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async () => {
    if (!currentQuestion || !answer.trim()) return;

    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/interview/questions/${currentQuestion.id}/answer`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question_id: currentQuestion.id,
            answer_text: answer,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to submit answer");
      }

      const feedbackData = await response.json();
      setFeedback(feedbackData);
    } catch (error) {
      console.error("Error submitting answer:", error);
      setError("Failed to submit answer");
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
        const audioBlob = new Blob(audioChunksRef.current, {
          type: "audio/wav",
        });
        await submitAudioAnswer(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error("Error starting recording:", error);
      setError("Failed to access microphone");
    }
  };

  const stopRecording = () => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== "inactive"
    ) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);

      // Stop all tracks
      mediaRecorderRef.current.stream
        .getTracks()
        .forEach((track) => track.stop());
    }
  };

  const submitAudioAnswer = async (audioBlob: Blob) => {
    if (!currentQuestion) return;

    const formData = new FormData();
    formData.append("audio_file", audioBlob, "answer.wav");

    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/interview/questions/${currentQuestion.id}/audio`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error("Failed to submit audio");
      }

      const feedbackData = await response.json();

      // Check if it's an error response
      if (feedbackData.error) {
        // Show error as a temporary alert
        setError(feedbackData.feedback);
        // Clear error after 5 seconds
        setTimeout(() => setError(null), 5000);
      } else {
        // Normal feedback
        setFeedback(feedbackData);
      }
    } catch (error) {
      console.error("Error submitting audio answer:", error);
      setError(
        "Failed to process audio. Please try again or type your answer."
      );
      setTimeout(() => setError(null), 5000);
    } finally {
      setLoading(false);
    }
  };

  const completeInterview = async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(
        `http://localhost:8000/api/interview/sessions/${sessionId}/complete`,
        {
          method: "PUT",
        }
      );

      if (!response.ok) {
        throw new Error("Failed to complete interview");
      }

      router.push(`/interview/results/${sessionId}`);
    } catch (error) {
      console.error("Error completing interview:", error);
      setError("Failed to complete interview");
    }
  };

  const formatTime = (seconds: number) => {
    if (seconds < 0) {
      console.warn("Negative time value:", seconds);
      return "0:00";
    }
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center p-8 bg-white rounded-lg shadow-lg">
          <div className="text-red-600 mb-4">
            <svg
              className="w-16 h-16 mx-auto"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Error</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => router.push("/interview/setup")}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Back to Setup
          </button>
        </div>
      </div>
    );
  }

  if (!session || !currentQuestion) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading interview...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Time Warning Modal */}
      {showTimeWarning && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md mx-4">
            <div className="text-center">
              <div className="text-yellow-600 mb-4">
                <svg
                  className="w-12 h-12 mx-auto"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Time Almost Up!
              </h3>
              <p className="text-gray-600 mb-4">
                Your interview will automatically end in{" "}
                {formatTime(timeRemaining)}. You&apos;ll be redirected to your
                results shortly.
              </p>
              <button
                onClick={() => completeSessionAndRedirect(sessionId)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Go to Results Now
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">
                {session.domain} Interview
              </h1>
              <p className="text-sm text-gray-600">Question {questionCount}</p>
            </div>
            <div className="text-right">
              <div
                className={`text-lg font-mono ${
                  timeRemaining <= 60 ? "text-red-600" : "text-gray-900"
                }`}
              >
                {formatTime(timeRemaining)} remaining
              </div>
              <div className="text-sm text-gray-600">
                {formatTime(elapsedTime)} elapsed
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Avatar Section */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <ProfessionalAvatar isPlaying={isPlayingTTS || isPlayingFeedbackTTS} analyser={analyser} />
            <div className="text-center mt-4">
              <button
                onClick={playQuestionAudio}
                disabled={isPlayingTTS}
                className={`px-4 py-2 rounded-lg text-sm ${
                  isPlayingTTS
                    ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                    : "bg-blue-600 text-white hover:bg-blue-700"
                }`}
              >
                {isPlayingTTS ? "Playing..." : "Play Question"}
              </button>
            </div>
          </div>

          {/* Question */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <div className="flex items-center mb-4">
              <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                {currentQuestion.question_type}
              </span>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
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
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 placeholder-gray-400"
                  />
                </div>

                <div className="flex space-x-4">
                  <button
                    onClick={submitAnswer}
                    disabled={!answer.trim() || loading}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300"
                  >
                    {loading ? "Submitting..." : "Submit Answer"}
                  </button>

                  <button
                    onClick={isRecording ? stopRecording : startRecording}
                    disabled={loading}
                    className={`px-6 py-2 rounded-lg ${
                      isRecording
                        ? "bg-red-600 text-white hover:bg-red-700"
                        : "bg-gray-600 text-white hover:bg-gray-700"
                    } disabled:bg-gray-300`}
                  >
                    {isRecording ? "⏹ Stop Recording" : "🎤 Record Answer"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Feedback */}
          {feedback && (
            <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  Feedback
                </h3>
                <button
                  onClick={playFeedbackAudio}
                  disabled={isPlayingFeedbackTTS}
                  className={`px-4 py-2 rounded-lg text-white font-medium transition-colors ${
                    isPlayingFeedbackTTS
                      ? "bg-gray-400 cursor-not-allowed"
                      : "bg-green-600 hover:bg-green-700"
                  }`}
                >
                  {isPlayingFeedbackTTS ? "Playing..." : "🎵 Play Feedback"}
                </button>
              </div>

              <div className="mb-4">
                <div className="flex items-center mb-2">
                  <span className="text-sm font-medium text-gray-700">
                    Score:
                  </span>
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
                  <h4 className="font-medium text-gray-700 mb-2">
                    Suggestions for Improvement:
                  </h4>
                  <ul className="list-disc list-inside text-gray-600 space-y-1">
                    {feedback.suggestions.map(
                      (suggestion: string, index: number) => (
                        <li key={index}>{suggestion}</li>
                      )
                    )}
                  </ul>
                </div>
              )}

              <div className="flex space-x-4">
                <button
                  onClick={getNextQuestion}
                  disabled={loading}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300"
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
