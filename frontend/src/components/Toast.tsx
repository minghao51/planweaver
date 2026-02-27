import { useEffect } from 'react';
import { X } from 'lucide-react';
import { motion } from 'framer-motion';
import { ToastType } from '../hooks/useToast';
import { cn } from '../utils';

interface ToastProps {
  id: string;
  message: string;
  type: ToastType;
  onClose: (id: string) => void;
}

const typeStyles: Record<ToastType, string> = {
  error: 'bg-red-500 text-white',
  success: 'bg-green-500 text-white',
  info: 'bg-blue-500 text-white',
};

export function Toast({ id, message, type, onClose }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(() => onClose(id), 5000);
    return () => clearTimeout(timer);
  }, [id, onClose]);

  return (
    <motion.div
      initial={{ opacity: 0, x: 100 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 100 }}
      className={cn(
        'flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg',
        'min-w-[300px] max-w-md',
        typeStyles[type]
      )}
      role="alert"
    >
      <span className="flex-1">{message}</span>
      <button
        onClick={() => onClose(id)}
        className="p-1 hover:bg-white/20 rounded"
        aria-label="Close"
      >
        <X size={16} />
      </button>
    </motion.div>
  );
}
