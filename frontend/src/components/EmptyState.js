import React from "react";
import { Sprout } from "lucide-react";

function EmptyState({ title, description, action, Icon = Sprout }) {
  return (
    <div className="mx-auto flex max-w-lg flex-col items-center py-8 text-center" role="status">
      <span className="flex h-11 w-11 items-center justify-center rounded-md bg-primary-50 text-primary-700" aria-hidden="true">
        <Icon size={21} strokeWidth={1.8} />
      </span>
      <p className="mt-3 text-base font-semibold text-text-heading">{title}</p>
      {description ? <p className="mt-1 max-w-md text-sm leading-6 text-text-muted">{description}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export default EmptyState;
