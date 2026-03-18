/**
 * Template 4: Simple full-page ChatGPT-style chat UI.
 * Cleanest possible Genie experience — no sidebar, no KPIs, pure conversation.
 */

import { motion } from "motion/react";
import { BRAND, CHAT_MESSAGES, SUGGESTED_QUERIES } from "./mock-data";
import { ChatMessageList, ChatInput } from "./ChatMessages";

export function SimpleChatDemo() {
  return (
    <div
      className="relative w-full h-full rounded-xl overflow-hidden border flex flex-col"
      style={{ background: BRAND.warmWhite }}
    >
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-3 border-b bg-white shrink-0">
        <img src={BRAND.logo} alt="Starbucks" className="h-8 w-8 object-contain" />
        <span className="text-base font-semibold" style={{ color: BRAND.secondary }}>
          Ask Genie
        </span>
      </div>

      {/* Welcome area + Messages */}
      <div className="flex-1 overflow-y-auto">
        {/* Welcome state */}
        <div className="flex flex-col items-center pt-10 pb-6 px-4">
          <img
            src={BRAND.logo}
            alt="Starbucks"
            className="h-16 w-16 object-contain opacity-30 mb-4"
          />
          <p className="text-sm text-gray-400 mb-5">
            Ask anything about your Starbucks data
          </p>
          <div className="flex flex-wrap justify-center gap-2 max-w-2xl">
            {SUGGESTED_QUERIES.map((sq) => (
              <motion.button
                key={sq.query}
                whileHover={{ scale: 1.03 }}
                className="px-3 py-1.5 rounded-full border text-xs text-gray-600 bg-white hover:border-gray-400 transition-colors cursor-pointer"
              >
                {sq.query}
              </motion.button>
            ))}
          </div>
        </div>

        {/* Messages */}
        <div className="max-w-3xl mx-auto">
          <ChatMessageList messages={CHAT_MESSAGES} />
        </div>
      </div>

      {/* Input bar */}
      <div className="max-w-3xl mx-auto w-full">
        <ChatInput />
      </div>
    </div>
  );
}
