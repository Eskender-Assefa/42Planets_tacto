# Strategic Negotiation Dashboard

Read and analyze the file i have attached for you. It will give you a context of what i am trying to build.  My current repo for this project is called "42Planets_tacto" and is found on my desktop. you can save any changes or files in that directory.      Add this raw data block to your Lovable prompt context so it knows how to handle layout states:

json

{
  "active_session": {
    "session_id": "case_wave1_04",
    "turn_number": 4,
    "seconds_left": 312,
    "current_status": "Active",
    "supplier": {
      "id": "brandlhuber_01",
      "name": "Gießerei Brandlhuber",
      "segment": "Strategic Partner",
      "country": "Germany"
    },
    "metrics": {
      "c_open": 142000.00,
      "c_current_offer": 131500.00,
      "c_best_floor": 122000.00,
      "current_score": 0.525
    },
    "audit_trail": {
      "concession_velocity": 0.004,
      "supplier_mindset": "Stalled",
      "observed_barrier": "Supplier hit a hard cost ceiling on base unit castings.",
      "strategic_intent": "Squeezing unit price is blocked. Shifting variables to an early liquidity lever.",
      "mathematical_justification": "Interest penalty offset by supplier baseline drop, netting +0.18 optimization."
    }
  }
}

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/28f19d5e-0ff8-4a27-a9cd-d8fd8e568dac).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
