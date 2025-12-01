// src/components/Card.tsx
import React from "react";

interface CardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ title, children, className }) => {
  const cls = ["card", className].filter(Boolean).join(" ");

  return (
    <div className={cls}>
      {title && <div className="card-header">{title}</div>}
      <div className="card-body">{children}</div>
    </div>
  );
};
