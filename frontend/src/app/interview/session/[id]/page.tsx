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
  const [error, setError] = useState<string | null>(null);

  // Audio related states
  const [isPlayingTTS, setIsPlayingTTS] = useState(false);
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null);
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const startTimeRef = useRef<Date | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setError("No session ID provided");
      return;
    }

    const initializeSession = async () => {
      try {
        // Fetch session details
        const response = await fetch(
          `http://localhost:8000/api/interview/sessions/${sessionId}`
        );
        if (!response.ok) {
          throw new Error("Failed to fetch session");
        }

        const sessionData = await response.json();
        setSession(sessionData);

        // Get first question
        console.log("Loading first question for session:", sessionId);
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
          const errorText = await questionResponse.text();
          console.error("Failed to get first question:", questionResponse.status, errorText);
          throw new Error(`Failed to get first question (${questionResponse.status})`);
        }

        const question = await questionResponse.json();
        
        if (question && question.question_text) {
          setCurrentQuestion(question);
          setQuestionCount(1);
          console.log(`First question loaded: ${question.question_text.substring(0, 50)}...`);
        } else {
          console.error("Invalid first question received:", question);
          throw new Error("Invalid question format received");
        }

        // Initialize audio context
        const AudioContextClass =
          window.AudioContext || window.webkitAudioContext;
        const ctx = new AudioContextClass();
        const analyserNode = ctx.createAnalyser();
        analyserNode.fftSize = 256;
        setAudioContext(ctx);
        setAnalyser(analyserNode);
      } catch (error) {
        console.error("Error initializing session:", error);
        setError(
          error instanceof Error
            ? error.message
            : "Failed to initialize session"
        );
      }
    };

    initializeSession();

    // Start timer
    startTimeRef.current = new Date();
    const timer = setInterval(() => {
      if (startTimeRef.current) {
        setElapsedTime(
          Math.floor((Date.now() - startTimeRef.current.getTime()) / 1000)
        );
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [sessionId]);

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

  const getNextQuestion = async () => {
    if (!session || !sessionId) {
      console.error("No session available");
      return;
    }

    // Prevent duplicate calls
    if (loading) {
      console.log("Already loading a question, skipping duplicate call");
      return;
    }

    setLoading(true);
    setError(null); // Clear any previous errors
    
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
            context: currentQuestion
              ? `Previous question: ${currentQuestion.question_text}`
              : null,
          }),
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Failed to get next question:", response.status, errorText);
        throw new Error(`Failed to get next question (${response.status})`);
      }

      const question = await response.json();
      
      // Only update if we got a valid question and it's different from current
      if (question && question.question_text && 
          (!currentQuestion || question.id !== currentQuestion.id)) {
        setCurrentQuestion(question);
        setAnswer("");
        setFeedback(null);
        setQuestionCount((prev) => prev + 1);
        console.log(`Successfully loaded question ${question.id}: ${question.question_text.substring(0, 50)}...`);
      } else {
        console.warn("Received invalid or duplicate question:", question);
        setError("Failed to generate a new question. Please try again.");
        setTimeout(() => setError(null), 4000);
      }
    } catch (error) {
      console.error("Error getting next question:", error);
      setError("Failed to get next question. Please try again.");
      setTimeout(() => setError(null), 5000);
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
      // Request microphone permission
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

      mediaRecorder.onerror = (event) => {
        console.error("MediaRecorder error:", event);
        setError("Recording error occurred. Please try again or type your answer.");
        setIsRecording(false);
        // Stop all tracks to clean up
        stream.getTracks().forEach((track) => track.stop());
        setTimeout(() => setError(null), 5000);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error("Error starting recording:", error);
      let errorMessage = "Failed to access microphone. ";
      
      if (error instanceof Error) {
        if (error.name === "NotAllowedError") {
          errorMessage += "Please allow microphone access and try again.";
        } else if (error.name === "NotFoundError") {
          errorMessage += "No microphone found. Please check your audio devices.";
        } else if (error.name === "NotSupportedError") {
          errorMessage += "Audio recording not supported in this browser.";
        } else {
          errorMessage += "Please try again or type your answer.";
        }
      } else {
        errorMessage += "Please try again or type your answer.";
      }
      
      setError(errorMessage);
      setIsRecording(false);
      // Clear error after 7 seconds for microphone errors
      setTimeout(() => setError(null), 7000);
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
    if (!currentQuestion) {
      setError("No current question available");
      setTimeout(() => setError(null), 3000);
      return;
    }

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
        const errorText = await response.text();
        console.error("Audio submission failed:", response.status, errorText);
        throw new Error(`Failed to submit audio (${response.status})`);
      }

      const feedbackData = await response.json();

      // Check if it's an error response
      if (feedbackData.error) {
        // Show error as a temporary alert but don't redirect
        console.warn("Speech-to-text error:", feedbackData.feedback);
        setError(`Speech recognition issue: ${feedbackData.feedback || 'Could not process audio'}. Please try recording again or type your answer.`);
        // Clear error after 6 seconds
        setTimeout(() => setError(null), 6000);
      } else {
        // Normal feedback - clear any previous errors
        setError(null);
        setFeedback(feedbackData);
      }
    } catch (error) {
      console.error("Error submitting audio answer:", error);
      
      let errorMessage = "Failed to process audio. ";
      if (error instanceof Error) {
        if (error.message.includes("NetworkError") || error.message.includes("fetch")) {
          errorMessage += "Network connection issue. Please check your connection and try again.";
        } else if (error.message.includes("500")) {
          errorMessage += "Server error processing audio. Please try recording again.";
        } else {
          errorMessage += error.message;
        }
      }
      errorMessage += " You can try recording again or type your answer instead.";
      
      setError(errorMessage);
      // Clear error after 8 seconds for processing errors
      setTimeout(() => setError(null), 8000);
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
              <div className="text-lg font-mono text-gray-900">{formatTime(elapsedTime)}</div>
              <div className="text-sm text-gray-600">
                {session.duration_minutes} min session
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Avatar Section */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <ProfessionalAvatar
              isPlaying={isPlayingTTS}
              analyser={analyser}
            />
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
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Feedback</h3>

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