package com.example.fitnesscoachai.ui.profile

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import com.example.fitnesscoachai.R
import com.example.fitnesscoachai.ui.auth.AuthActivity

class ProfileFragment : Fragment() {
    
    private lateinit var btnLogout: Button

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        val view = inflater.inflate(R.layout.fragment_profile, container, false)
        
        btnLogout = view.findViewById(R.id.btnLogout)
        btnLogout.setOnClickListener {
            requireActivity()
                .getSharedPreferences("auth", AppCompatActivity.MODE_PRIVATE)
                .edit()
                .clear()
                .apply()

            startActivity(Intent(requireContext(), AuthActivity::class.java))
            requireActivity().finish()
        }
        
        return view
    }
}

