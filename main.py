"""
ArcVault Protocol - Autonomous USDC Safe & Financial Agent Gateway
BLI LegalTech Hackathon 2
License: MIT
"""

import time
import uuid
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="ArcVault USDC Autonomous Gateway",
    description="Micro-treasury & Automated Escrow Vault for AI Agents",
    version="1.0.0"
)

vaults_db: Dict[str, dict] = {}
audit_trail: List[dict] = []

class VaultCreationRequest(BaseModel):
    owner_address: str = Field(..., description="Owner Web3 Wallet Address")
    agent_delegate: str = Field(..., description="Authorized Agent Address")
    daily_spend_limit_usdc: float = Field(..., gt=0, description="Daily spending ceiling in USDC")
    per_tx_limit_usdc: float = Field(..., gt=0, description="Single transaction ceiling in USDC")

class AgentTransferRequest(BaseModel):
    vault_id: str = Field(..., description="Vault ID")
    agent_address: str = Field(..., description="Executing Agent Address")
    recipient_address: str = Field(..., description="Payment Recipient Address")
    amount_usdc: float = Field(..., gt=0, description="Transfer Amount in USDC")
    memo: str = Field(..., description="Audit rationale / service payment reference")

@app.get("/")
def health_check():
    return {
        "protocol": "ArcVault USDC Safe",
        "status": "ONLINE",
        "active_vaults": len(vaults_db),
        "total_executions": len(audit_trail)
    }

@app.post("/api/v1/vault/create", status_code=status.HTTP_201_CREATED)
def create_vault(req: VaultCreationRequest):
    vault_id = f"vault_{uuid.uuid4().hex[:8]}"
    vault_record = {
        "vault_id": vault_id,
        "owner": req.owner_address,
        "agent_delegate": req.agent_delegate,
        "balance_usdc": 1000.0,
        "daily_limit": req.daily_spend_limit_usdc,
        "per_tx_limit": req.per_tx_limit_usdc,
        "spent_today": 0.0,
        "created_at": int(time.time()),
        "status": "ACTIVE"
    }
    vaults_db[vault_id] = vault_record
    return {"status": "SUCCESS", "vault": vault_record}

@app.post("/api/v1/vault/transfer")
def execute_agent_transfer(req: AgentTransferRequest):
    if req.vault_id not in vaults_db:
        raise HTTPException(status_code=404, detail="Target vault not found")
    
    vault = vaults_db[req.vault_id]
    
    if vault["agent_delegate"] != req.agent_address:
        raise HTTPException(status_code=403, detail="Unauthorized agent address")
    
    if req.amount_usdc > vault["per_tx_limit"]:
        raise HTTPException(status_code=400, detail="Exceeds per-transaction limit")
        
    if (vault["spent_today"] + req.amount_usdc) > vault["daily_limit"]:
        raise HTTPException(status_code=400, detail="Exceeds daily spending limit")

    vault["balance_usdc"] -= req.amount_usdc
    vault["spent_today"] += req.amount_usdc

    tx_record = {
        "tx_hash": f"0x{uuid.uuid4().hex}",
        "vault_id": req.vault_id,
        "agent": req.agent_address,
        "recipient": req.recipient_address,
        "amount_usdc": req.amount_usdc,
        "memo": req.memo,
        "timestamp": int(time.time())
    }
    audit_trail.append(tx_record)
    return {"status": "TRANSFER_EXECUTED", "receipt": tx_record}

@app.get("/api/v1/audit/logs")
def get_audit_trail():
    return {"total": len(audit_trail), "logs": audit_trail}
