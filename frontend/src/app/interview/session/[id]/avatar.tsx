import React, { useEffect, useRef } from 'react';

interface InterviewAvatarProps {
  isPlaying: boolean;
  analyser: AnalyserNode | null;
}

export default function ProfessionalAvatar({ isPlaying, analyser }: InterviewAvatarProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size for high DPI displays
    const scale = window.devicePixelRatio || 1;
    canvas.width = 400 * scale;
    canvas.height = 400 * scale;
    ctx.scale(scale, scale);

    let mouthOpenness = 0;
    let targetMouthOpenness = 0;
    const smoothingFactor = 0.3;

    const draw = () => {
      animationRef.current = requestAnimationFrame(draw);

      // Clear canvas with gradient background
      const gradient = ctx.createLinearGradient(0, 0, 400, 400);
      gradient.addColorStop(0, '#f0f9ff');
      gradient.addColorStop(1, '#e0f2fe');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, 400, 400);

      // Get audio data if playing
      if (isPlaying && analyser) {
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        analyser.getByteFrequencyData(dataArray);
        
        // Calculate average volume for mouth animation
        const average = dataArray.reduce((a, b) => a + b) / bufferLength;
        targetMouthOpenness = Math.min(average / 3, 25);
      } else {
        targetMouthOpenness = 0;
      }

      // Smooth mouth animation
      mouthOpenness += (targetMouthOpenness - mouthOpenness) * smoothingFactor;

      // Draw professional avatar
      const centerX = 200;
      const centerY = 200;

      // Head shadow
      ctx.save();
      ctx.shadowColor = 'rgba(0, 0, 0, 0.1)';
      ctx.shadowBlur = 20;
      ctx.shadowOffsetY = 10;
      
      // Head shape (more realistic proportions)
      ctx.beginPath();
      ctx.ellipse(centerX, centerY - 10, 85, 95, 0, 0, 2 * Math.PI);
      ctx.fillStyle = '#fbbf24'; // Warm skin tone
      ctx.fill();
      ctx.restore();

      // Hair
      ctx.beginPath();
      ctx.ellipse(centerX, centerY - 60, 75, 45, 0, Math.PI, 2 * Math.PI);
      ctx.fillStyle = '#1f2937';
      ctx.fill();

      // Hair details
      ctx.beginPath();
      ctx.ellipse(centerX - 20, centerY - 70, 30, 25, -0.3, Math.PI * 0.8, Math.PI * 1.5);
      ctx.fill();
      ctx.beginPath();
      ctx.ellipse(centerX + 20, centerY - 70, 30, 25, 0.3, Math.PI * 1.5, Math.PI * 2.2);
      ctx.fill();

      // Ears
      ctx.fillStyle = '#fbbf24';
      ctx.beginPath();
      ctx.ellipse(centerX - 80, centerY - 10, 15, 25, -0.1, 0, 2 * Math.PI);
      ctx.fill();
      ctx.beginPath();
      ctx.ellipse(centerX + 80, centerY - 10, 15, 25, 0.1, 0, 2 * Math.PI);
      ctx.fill();

      // Glasses frame
      ctx.strokeStyle = '#1f2937';
      ctx.lineWidth = 3;
      
      // Left lens
      ctx.beginPath();
      ctx.ellipse(centerX - 30, centerY - 20, 28, 25, 0, 0, 2 * Math.PI);
      ctx.stroke();
      
      // Right lens
      ctx.beginPath();
      ctx.ellipse(centerX + 30, centerY - 20, 28, 25, 0, 0, 2 * Math.PI);
      ctx.stroke();
      
      // Bridge
      ctx.beginPath();
      ctx.moveTo(centerX - 2, centerY - 20);
      ctx.lineTo(centerX + 2, centerY - 20);
      ctx.stroke();

      // Eyes
      ctx.fillStyle = '#1f2937';
      // Left eye
      ctx.beginPath();
      ctx.ellipse(centerX - 30, centerY - 20, 8, 10, 0, 0, 2 * Math.PI);
      ctx.fill();
      
      // Right eye
      ctx.beginPath();
      ctx.ellipse(centerX + 30, centerY - 20, 8, 10, 0, 0, 2 * Math.PI);
      ctx.fill();

      // Eye shine
      ctx.fillStyle = 'white';
      ctx.beginPath();
      ctx.ellipse(centerX - 28, centerY - 22, 3, 3, 0, 0, 2 * Math.PI);
      ctx.fill();
      ctx.beginPath();
      ctx.ellipse(centerX + 32, centerY - 22, 3, 3, 0, 0, 2 * Math.PI);
      ctx.fill();

      // Nose
      ctx.strokeStyle = '#e5a317';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(centerX, centerY - 5);
      ctx.quadraticCurveTo(centerX + 10, centerY + 10, centerX, centerY + 15);
      ctx.stroke();

      // Mouth
      ctx.strokeStyle = '#dc2626';
      ctx.fillStyle = '#dc2626';
      ctx.lineWidth = 3;
      
      if (mouthOpenness > 5) {
        // Open mouth
        ctx.beginPath();
        ctx.ellipse(centerX, centerY + 35, 25, mouthOpenness, 0, 0, Math.PI);
        ctx.fillStyle = '#1f2937';
        ctx.fill();
        ctx.stroke();
        
        // Teeth hint
        if (mouthOpenness > 10) {
          ctx.fillStyle = 'white';
          ctx.fillRect(centerX - 15, centerY + 35, 30, 5);
        }
      } else {
        // Closed mouth smile
        ctx.beginPath();
        ctx.arc(centerX, centerY + 25, 20, 0.2 * Math.PI, 0.8 * Math.PI);
        ctx.stroke();
      }

      // Professional collar/shirt
      ctx.fillStyle = '#3b82f6';
      ctx.beginPath();
      ctx.moveTo(centerX - 100, 350);
      ctx.lineTo(centerX - 60, centerY + 80);
      ctx.lineTo(centerX - 30, centerY + 85);
      ctx.lineTo(centerX, centerY + 90);
      ctx.lineTo(centerX + 30, centerY + 85);
      ctx.lineTo(centerX + 60, centerY + 80);
      ctx.lineTo(centerX + 100, 350);
      ctx.lineTo(centerX + 100, 400);
      ctx.lineTo(centerX - 100, 400);
      ctx.closePath();
      ctx.fill();

      // Collar details
      ctx.fillStyle = 'white';
      ctx.beginPath();
      ctx.moveTo(centerX - 30, centerY + 85);
      ctx.lineTo(centerX - 40, centerY + 100);
      ctx.lineTo(centerX - 20, centerY + 100);
      ctx.closePath();
      ctx.fill();
      
      ctx.beginPath();
      ctx.moveTo(centerX + 30, centerY + 85);
      ctx.lineTo(centerX + 40, centerY + 100);
      ctx.lineTo(centerX + 20, centerY + 100);
      ctx.closePath();
      ctx.fill();

      // Tie
      ctx.fillStyle = '#1e40af';
      ctx.beginPath();
      ctx.moveTo(centerX, centerY + 90);
      ctx.lineTo(centerX - 10, centerY + 105);
      ctx.lineTo(centerX - 8, 350);
      ctx.lineTo(centerX, 360);
      ctx.lineTo(centerX + 8, 350);
      ctx.lineTo(centerX + 10, centerY + 105);
      ctx.closePath();
      ctx.fill();

      // Audio visualization - professional style
      if (isPlaying && analyser) {
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        analyser.getByteFrequencyData(dataArray);

        // Professional audio bars at bottom
        const barWidth = 2;
        const barGap = 3;
        const barCount = 60;
        const startX = centerX - (barCount * (barWidth + barGap)) / 2;

        for (let i = 0; i < barCount; i++) {
          const dataIndex = Math.floor(i * bufferLength / barCount);
          const barHeight = (dataArray[dataIndex] || 0) / 4;
          
          const x = startX + i * (barWidth + barGap);
          const hue = 200 + (i / barCount) * 30; // Blue to teal gradient
          
          ctx.fillStyle = `hsla(${hue}, 70%, 50%, 0.8)`;
          ctx.fillRect(x, 380 - barHeight, barWidth, barHeight);
        }
      }

      // Name badge
      ctx.fillStyle = 'white';
      ctx.fillRect(centerX - 40, 320, 80, 25);
      ctx.strokeStyle = '#e5e7eb';
      ctx.lineWidth = 1;
      ctx.strokeRect(centerX - 40, 320, 80, 25);
      
      ctx.fillStyle = '#1f2937';
      ctx.font = '12px Arial';
      ctx.textAlign = 'center';
      ctx.fillText('AI Interviewer', centerX, 337);
    };

    draw();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isPlaying, analyser]);

  return (
    <div className="flex flex-col items-center">
      <canvas 
        ref={canvasRef} 
        width={400} 
        height={400}
        style={{ width: '400px', height: '400px' }}
        className="rounded-lg shadow-lg"
      />
      <div className="mt-4 text-center">
        <h3 className="text-lg font-semibold text-gray-800">AI Interview Assistant</h3>
        <p className="text-sm text-gray-600">Professional Technical Interviewer</p>
      </div>
    </div>
  );
}