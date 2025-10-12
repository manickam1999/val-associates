"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"

export type Mode = "everything" | "minimal"

interface ModeSelectorProps {
  selectedModes: Mode[]
  onChange: (modes: Mode[]) => void
}

export function ModeSelector({ selectedModes, onChange }: ModeSelectorProps) {
  const handleToggle = (mode: Mode) => {
    if (selectedModes.includes(mode)) {
      // Don't allow deselecting if it's the last one
      if (selectedModes.length === 1) return
      onChange(selectedModes.filter((m) => m !== mode))
    } else {
      onChange([...selectedModes, mode])
    }
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-3">
          <Label className="text-base font-semibold">Output Mode</Label>
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="everything"
                checked={selectedModes.includes("everything")}
                onCheckedChange={() => handleToggle("everything")}
              />
              <label
                htmlFor="everything"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
              >
                Everything - Full extraction (all columns)
              </label>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="minimal"
                checked={selectedModes.includes("minimal")}
                onCheckedChange={() => handleToggle("minimal")}
              />
              <label
                htmlFor="minimal"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
              >
                Minimal - Essential columns only (12 columns)
              </label>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}