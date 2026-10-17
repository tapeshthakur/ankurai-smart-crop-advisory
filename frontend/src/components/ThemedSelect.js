import React from "react";

function ThemedSelect({ label, value, options, onChange, className = "", ...props }) {
  return (
    <select
      aria-label={label}
      className={`theme-select ${className}`}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      {...props}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

export default ThemedSelect;
