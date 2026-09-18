import { API_CONFIG } from '../config/api';
import { getToken } from './authService';

export interface PaymentPlan {
  id: 'starter' | 'pro' | 'enterprise';
  name: string;
  tagline: string;
  price_usd_monthly: number;
  price_bdt_monthly: number;
  comparisons_included: string | number;
  popular: boolean;
  features: string[];
}

export interface PaymentGateway {
  id: 'bkash';
  name: string;
  types: string[];
  currency: string;
  icon: string;
  active: boolean;
}

export interface CheckoutRequest {
  plan_id: string;
  billing_cycle: 'monthly' | 'annual';
  payment_method: 'bkash';
  bkash_details: {
    phone_number: string;
    otp?: string;
    pin?: string;
  };
}

export interface CheckoutResponse {
  status: 'success' | 'failed';
  message: string;
  transaction_id: string;
  plan_id: string;
  plan_name: string;
  billing_cycle: 'monthly' | 'annual';
  payment_method: 'bkash';
  amount_formatted: string;
  amount_usd: number;
  amount_bdt: number;
  gateway_message: string;
  timestamp: string;
  invoice_pdf_url?: string;
}

export interface BkashCreateResponse {
  status: 'success' | 'failed';
  paymentID: string;
  bkashURL: string;
  statusCode: string;
  statusMessage: string;
  invoiceNumber: string;
  amount_bdt: number;
}

export async function createBkashPayment(
  planId: string,
  billingCycle: 'monthly' | 'annual',
  payerReference: string = '01711111111'
): Promise<BkashCreateResponse> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_CONFIG.baseUrl}/api/bkash/create`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      plan_id: planId,
      billing_cycle: billingCycle,
      payer_reference: payerReference,
    }),
  });

  const resData = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(resData?.detail || resData?.message || 'Failed to initiate bKash payment.');
  }

  return resData as BkashCreateResponse;
}

export async function executeBkashPayment(paymentID: string): Promise<CheckoutResponse> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_CONFIG.baseUrl}/api/bkash/execute`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ paymentID }),
  });

  const resData = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(resData?.detail || resData?.message || 'bKash payment execution & verification failed.');
  }

  return resData as CheckoutResponse;
}


export async function fetchPaymentPlans(): Promise<{ plans: PaymentPlan[]; gateways: PaymentGateway[] }> {
  try {
    const res = await fetch(`${API_CONFIG.baseUrl}/api/payment/plans`);
    if (res.ok) {
      return await res.json();
    }
  } catch {
    // Return fallback plans if offline or server not ready
  }

  return {
    gateways: [
      { id: 'bkash', name: 'bKash', types: ['bKash Wallet', 'MFS Direct Payment'], currency: 'BDT', icon: 'bkash', active: true }
    ],
    plans: [
      {
        id: 'starter',
        name: 'Starter',
        tagline: 'Ideal for individual engineers & small projects',
        price_usd_monthly: 19,
        price_bdt_monthly: 2200,
        comparisons_included: 50,
        popular: false,
        features: [
          '50 AI drawing comparisons / mo',
          'Sub-pixel ORB homography alignment',
          'PNG & PDF drawing support',
          'Basic ECO summary export',
          'Email support',
        ]
      },
      {
        id: 'pro',
        name: 'Professional',
        tagline: 'For engineering teams needing full compliance & VLM',
        price_usd_monthly: 79,
        price_bdt_monthly: 9200,
        comparisons_included: 'Unlimited',
        popular: true,
        features: [
          'Unlimited AI drawing comparisons',
          'Gemini Flash VLM change classification',
          'ISO 10209 & ASME Y14.5 compliance logs',
          'Annotated PDF & High-Res PNG Export',
          'Multi-page PDF auto page-matching',
          'Priority 24/7 technical support',
        ]
      },
      {
        id: 'enterprise',
        name: 'Enterprise Team',
        tagline: 'Custom integration for aerospace & CAD manufacturing',
        price_usd_monthly: 249,
        price_bdt_monthly: 28900,
        comparisons_included: 'Unlimited',
        popular: false,
        features: [
          'Unlimited seat licenses for team',
          'REST API & Python SDK access',
          'Dedicated CAD server infrastructure',
          'SOC2 & ISO 27001 data confidentiality',
          'Custom VLM model fine-tuning',
          'Dedicated Solutions Engineer',
        ]
      }
    ]
  };
}
