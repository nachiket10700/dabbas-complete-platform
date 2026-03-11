"""
Email Service Module
Handles all email communications for the platform
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailService:
    """Handle all email notifications"""
    
    def __init__(self, smtp_server=None, smtp_port=None, username=None, password=None, from_email=None):
        # In development, we'll just log emails
        self.smtp_server = smtp_server or 'smtp.gmail.com'
        self.smtp_port = smtp_port or 587
        self.username = username or 'noreply@dabbas.com'
        self.password = password or 'your-password'
        self.from_email = from_email or 'noreply@dabbas.com'
        self.from_name = 'Dabba\'s Support'
        
        # For development, we'll simulate sending
        self.dev_mode = True
        logger.info("Email Service initialized (Development Mode)")
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None):
        """Send an email"""
        try:
            if self.dev_mode:
                # Just log the email in development
                logger.info(f"📧 EMAIL TO: {to_email}")
                logger.info(f"📧 SUBJECT: {subject}")
                logger.info(f"📧 CONTENT: {html_content[:200]}...")
                return True
            
            # In production, actually send the email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add plain text version
            if text_content:
                part1 = MIMEText(text_content, 'plain')
                msg.attach(part1)
            
            # Add HTML version
            part2 = MIMEText(html_content, 'html')
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_welcome_email(self, email: str, name: str):
        """Send welcome email to new user"""
        subject = "Welcome to Dabba's!"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #ff6b6b, #4ecdc4); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Dabba's</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>Welcome, {name}!</h2>
                    <p>Thank you for joining Dabba's - India's most trusted tiffin service.</p>
                    <p>We're excited to bring delicious, home-style meals right to your doorstep.</p>
                    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3>Getting Started:</h3>
                        <ul>
                            <li>Set your dietary preferences</li>
                            <li>Choose your favorite cuisines</li>
                            <li>Select a subscription plan</li>
                            <li>Get your first meal delivered!</li>
                        </ul>
                    </div>
                    <a href="https://dabbas.com/customer/dashboard" 
                       style="display: inline-block; background: #ff6b6b; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; margin-top: 20px;">
                        Go to Dashboard
                    </a>
                </div>
                <div style="background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p>&copy; 2025 Dabba's. All rights reserved.</p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(email, subject, html_content)
    
    def send_subscription_confirmation(self, email: str, name: str, plan: Dict):
        """Send subscription confirmation email"""
        subject = f"Subscription Confirmed - {plan.get('name', 'Dabba\'s Plan')}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #ff6b6b, #4ecdc4); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Dabba's</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>Subscription Confirmed! 🎉</h2>
                    <p>Dear {name},</p>
                    <p>Your subscription to <strong>{plan.get('name')}</strong> has been successfully activated.</p>
                    
                    <div style="background-color: #e8f5e9; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        <h3>Plan Details:</h3>
                        <p><strong>Plan:</strong> {plan.get('name')}</p>
                        <p><strong>Price:</strong> ₹{plan.get('price')}</p>
                        <p><strong>Meals per day:</strong> {plan.get('meals_per_day', 1)}</p>
                    </div>
                    
                    <p>Your first meal will be delivered according to your preferred schedule.</p>
                    
                    <a href="https://dabbas.com/customer/subscriptions" 
                       style="display: inline-block; background: #4ecdc4; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; margin-top: 20px;">
                        Manage Subscription
                    </a>
                </div>
                <div style="background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p>&copy; 2025 Dabba's. All rights reserved.</p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(email, subject, html_content)
    
    def send_payment_confirmation(self, email: str, payment_id: str, amount: float):
        """Send payment confirmation email"""
        subject = f"Payment Confirmed - ₹{amount}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #ff6b6b, #4ecdc4); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Dabba's</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>Payment Successful! ✅</h2>
                    <p>Your payment has been processed successfully.</p>
                    
                    <div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        <h3>Transaction Details:</h3>
                        <p><strong>Transaction ID:</strong> {payment_id}</p>
                        <p><strong>Amount:</strong> ₹{amount}</p>
                        <p><strong>Date:</strong> {datetime.now().strftime('%d %b %Y, %I:%M %p')}</p>
                        <p><strong>Status:</strong> Completed</p>
                    </div>
                    
                    <p>Thank you for your payment. Your order is being processed.</p>
                    
                    <a href="https://dabbas.com/customer/orders" 
                       style="display: inline-block; background: #ff6b6b; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; margin-top: 20px;">
                        View Orders
                    </a>
                </div>
                <div style="background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p>&copy; 2025 Dabba's. All rights reserved.</p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(email, subject, html_content)
    
    def send_complaint_confirmation(self, email: str, complaint_id: str):
        """Send complaint confirmation email"""
        subject = f"Complaint Registered - #{complaint_id}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #ff6b6b, #4ecdc4); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Dabba's</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>Complaint Registered 📝</h2>
                    <p>Your complaint has been registered successfully.</p>
                    
                    <div style="background-color: #fff3e0; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        <h3>Complaint Details:</h3>
                        <p><strong>Complaint ID:</strong> {complaint_id}</p>
                        <p><strong>Status:</strong> Under Review</p>
                        <p><strong>Expected Response:</strong> Within 24 hours</p>
                    </div>
                    
                    <p>Our support team will look into this matter and get back to you soon.</p>
                    
                    <a href="https://dabbas.com/customer/complaints/{complaint_id}" 
                       style="display: inline-block; background: #4ecdc4; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; margin-top: 20px;">
                        Track Complaint
                    </a>
                </div>
                <div style="background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p>&copy; 2025 Dabba's. All rights reserved.</p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(email, subject, html_content)
    
    def send_complaint_update(self, email: str, complaint_id: str):
        """Send complaint update notification"""
        subject = f"Update on Complaint #{complaint_id}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #ff6b6b, #4ecdc4); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Dabba's</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>Complaint Update</h2>
                    <p>There's a new update on your complaint <strong>#{complaint_id}</strong>.</p>
                    
                    <p>A support representative has responded to your complaint.</p>
                    
                    <a href="https://dabbas.com/customer/complaints/{complaint_id}" 
                       style="display: inline-block; background: #ff6b6b; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; margin-top: 20px;">
                        View Response
                    </a>
                </div>
                <div style="background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p>&copy; 2025 Dabba's. All rights reserved.</p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(email, subject, html_content)
    
    def send_complaint_resolved(self, email: str, complaint_id: str, resolution: str):
        """Send complaint resolved notification"""
        subject = f"Complaint Resolved - #{complaint_id}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #ff6b6b, #4ecdc4); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Dabba's</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>Complaint Resolved ✅</h2>
                    <p>Your complaint <strong>#{complaint_id}</strong> has been resolved.</p>
                    
                    <div style="background-color: #e8f5e9; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        <h3>Resolution:</h3>
                        <p>{resolution}</p>
                    </div>
                    
                    <p>We hope you're satisfied with the resolution. Your feedback helps us improve.</p>
                    
                    <a href="https://dabbas.com/customer/complaints/{complaint_id}" 
                       style="display: inline-block; background: #4ecdc4; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; margin-top: 20px;">
                        Rate Resolution
                    </a>
                </div>
                <div style="background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p>&copy; 2025 Dabba's. All rights reserved.</p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(email, subject, html_content)
    
    def send_complaint_resolved_provider(self, email: str, complaint_id: str, resolution: str):
        """Send complaint resolved notification to provider"""
        subject = f"Complaint Resolved - #{complaint_id}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #ff6b6b, #4ecdc4); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Dabba's</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>Complaint Resolved</h2>
                    <p>A complaint <strong>#{complaint_id}</strong> has been resolved.</p>
                    
                    <div style="background-color: #e8f5e9; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        <h3>Resolution:</h3>
                        <p>{resolution}</p>
                    </div>
                    
                    <p>Thank you for your cooperation in resolving this matter.</p>
                </div>
                <div style="background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p>&copy; 2025 Dabba's. All rights reserved.</p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(email, subject, html_content)
    
    def send_new_complaint_notification(self, email: str, complaint_id: str):
        """Send notification about new complaint to provider"""
        subject = f"New Complaint Received - #{complaint_id}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #ff6b6b, #4ecdc4); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Dabba's</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>New Complaint Received</h2>
                    <p>A new complaint <strong>#{complaint_id}</strong> has been filed against your business.</p>
                    
                    <p>Please review and respond to this complaint as soon as possible.</p>
                    
                    <a href="https://dabbas.com/provider/complaints/{complaint_id}" 
                       style="display: inline-block; background: #ff6b6b; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; margin-top: 20px;">
                        View Complaint
                    </a>
                </div>
                <div style="background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p>&copy; 2025 Dabba's. All rights reserved.</p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(email, subject, html_content)
    
    def send_escalated_complaint_notification(self, email: str, complaint_id: str):
        """Send notification about escalated complaint to owner"""
        subject = f"Complaint Escalated - #{complaint_id}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #ff6b6b, #4ecdc4); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Dabba's</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>Complaint Escalated ⚠️</h2>
                    <p>Complaint <strong>#{complaint_id}</strong> has been escalated to management.</p>
                    
                    <p>Please review this complaint and take appropriate action.</p>
                    
                    <a href="https://dabbas.com/owner/complaints/{complaint_id}" 
                       style="display: inline-block; background: #ff6b6b; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; margin-top: 20px;">
                        Review Complaint
                    </a>
                </div>
                <div style="background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p>&copy; 2025 Dabba's. All rights reserved.</p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(email, subject, html_content)
    
    def send_provider_registration_confirmation(self, email: str, business_name: str):
        """Send provider registration confirmation"""
        subject = "Provider Registration Received"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #ff6b6b, #4ecdc4); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Dabba's</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>Registration Received!</h2>
                    <p>Thank you for registering <strong>{business_name}</strong> with Dabba's.</p>
                    
                    <div style="background-color: #fff3e0; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        <h3>Next Steps:</h3>
                        <ol>
                            <li>Our team will review your application</li>
                            <li>We'll verify your documents</li>
                            <li>You'll receive a verification email within 2-3 business days</li>
                            <li>Once verified, you can start receiving orders!</li>
                        </ol>
                    </div>
                    
                    <p>We'll notify you once your account is verified.</p>
                </div>
                <div style="background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p>&copy; 2025 Dabba's. All rights reserved.</p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(email, subject, html_content)
    
    def send_provider_verification_confirmation(self, email: str, business_name: str):
        """Send provider verification confirmation"""
        subject = "Your Business is Now Verified!"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #ff6b6b, #4ecdc4); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Dabba's</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>Congratulations! 🎉</h2>
                    <p><strong>{business_name}</strong> has been verified successfully!</p>
                    
                    <div style="background-color: #e8f5e9; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        <h3>What's Next:</h3>
                        <ul>
                            <li>Add your menu items</li>
                            <li>Set your operating hours</li>
                            <li>Configure delivery zones</li>
                            <li>Start receiving orders!</li>
                        </ul>
                    </div>
                    
                    <a href="https://dabbas.com/provider/dashboard" 
                       style="display: inline-block; background: #4ecdc4; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; margin-top: 20px;">
                        Go to Provider Dashboard
                    </a>
                </div>
                <div style="background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p>&copy; 2025 Dabba's. All rights reserved.</p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(email, subject, html_content)
    
    def send_provider_rejection_notification(self, email: str, business_name: str, reason: str = None):
        """Send provider rejection notification"""
        subject = "Update on Your Provider Application"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #ff6b6b, #4ecdc4); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Dabba's</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>Application Status Update</h2>
                    <p>Dear Partner,</p>
                    <p>Thank you for your interest in partnering with Dabba's.</p>
                    
                    <div style="background-color: #ffebee; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        <p>After reviewing your application for <strong>{business_name}</strong>, we regret to inform you that we are unable to verify your business at this time.</p>
                        {f'<p><strong>Reason:</strong> {reason}</p>' if reason else ''}
                    </div>
                    
                    <p>You're welcome to reapply after addressing the above concerns.</p>
                    
                    <a href="https://dabbas.com/contact" 
                       style="display: inline-block; background: #ff6b6b; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; margin-top: 20px;">
                        Contact Support
                    </a>
                </div>
                <div style="background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p>&copy; 2025 Dabba's. All rights reserved.</p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(email, subject, html_content)
    
    def send_contact_form(self, name: str, email: str, phone: str = None, message: str = None):
        """Send contact form submission to support"""
        subject = f"New Contact Form Submission from {name}"
        html_content = f"""
        <html>
            <body>
                <h2>New Contact Form Submission</h2>
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Email:</strong> {email}</p>
                {f'<p><strong>Phone:</strong> {phone}</p>' if phone else ''}
                <p><strong>Message:</strong></p>
                <p>{message}</p>
            </body>
        </html>
        """
        
        # Send to support email
        support_email = 'support@dabbas.com'
        return self.send_email(support_email, subject, html_content)
    
    def send_contact_auto_reply(self, email: str, name: str):
        """Send auto-reply to contact form submission"""
        subject = "Thank You for Contacting Dabba's"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #ff6b6b, #4ecdc4); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Dabba's</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>Thank You for Reaching Out!</h2>
                    <p>Dear {name},</p>
                    <p>We've received your message and will get back to you within 24 hours.</p>
                    
                    <p>In the meantime, you might find answers in our <a href="https://dabbas.com/faq">FAQ section</a>.</p>
                    
                    <p>Have a great day!</p>
                    <p>- The Dabba's Team</p>
                </div>
                <div style="background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p>&copy; 2025 Dabba's. All rights reserved.</p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(email, subject, html_content)

    def send_password_reset(self, email: str, reset_link: str):
        """Send password reset email"""
        subject = "Reset Your Password - Dabba's"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #ff6b6b, #ff8e8e); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Dabba\'s</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>Reset Your Password</h2>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_link}" style="background: #ff6b6b; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                            Reset Password
                        </a>
                    </div>
                    <p>Or copy this link: <br> <small>{reset_link}</small></p>
                    <p>This link will expire in 24 hours.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #999; font-size: 12px;">&copy; 2025 Dabba\'s. All rights reserved.</p>
                </div>
            </body>
        </html>
        """
        return self.send_email(email, subject, html_content)